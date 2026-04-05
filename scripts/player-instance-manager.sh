#!/usr/bin/env bash
set -euo pipefail

INSTANCES_ROOT="/opt/ctf/instances"
LEASES_ROOT="/opt/ctf/leases"
PORT_MIN=6100
PORT_MAX=6999

usage() {
  cat <<EOF
Usage:
  $0 start --challenge <name> --team <team-id> [--ttl-min 60] [--port 6201]
  $0 stop --challenge <name> --team <team-id>
  $0 extend --challenge <name> --team <team-id> [--ttl-min 30]
  $0 status
  $0 cleanup
EOF
}

sanitize() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[[:space:]]+/-/g' | tr -cd 'a-z0-9-' | sed -E 's/-+/-/g; s/^-+//; s/-+$//'
}

legacy_sanitize() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-'
}

lease_file_for() {
  local challenge="$1"
  local team="$2"
  echo "$LEASES_ROOT/inst_${challenge}_${team}.env"
}

project_for() {
  local challenge="$1"
  local team="$2"
  echo "inst_${challenge}_${team}"
}

is_port_used() {
  local port="$1"
  ss -lnt 2>/dev/null | awk '{print $4}' | grep -Eq ":${port}$"
}

find_free_port() {
  local p
  for ((p=PORT_MIN; p<=PORT_MAX; p++)); do
    if ! is_port_used "$p"; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

ensure_dirs() {
  sudo mkdir -p "$INSTANCES_ROOT" "$LEASES_ROOT"
}

resolve_challenge_dir() {
  local challenge="$1"
  local base="/vagrant/challenges"
  local direct="$base/$challenge"

  if [[ -d "$direct" && -f "$direct/challenge.yml" ]]; then
    echo "$direct"
    return 0
  fi

  local yml dir
  while IFS= read -r -d '' yml; do
    dir=$(dirname "$yml")
    local folder
    folder=$(basename "$dir")
    if [[ "$(sanitize "$folder")" == "$challenge" ]]; then
      echo "$dir"
      return 0
    fi

    local yml_name
    yml_name=$(grep -E '^name:' "$dir/challenge.yml" | sed -E 's/^name:[[:space:]]*//' | tr -d '"\r' | head -1 || true)
    if [[ -n "$yml_name" && "$(sanitize "$yml_name")" == "$challenge" ]]; then
      echo "$dir"
      return 0
    fi
  done < <(find "$base" -type f -name challenge.yml -print0 2>/dev/null)

  return 1
}

write_lease() {
  local lease_file="$1"
  local challenge="$2"
  local team="$3"
  local project="$4"
  local instance_dir="$5"
  local port="$6"
  local ttl_min="$7"
  local expires_epoch="$8"

  sudo tee "$lease_file" >/dev/null <<EOF
CHALLENGE=${challenge}
TEAM=${team}
PROJECT=${project}
INSTANCE_DIR=${instance_dir}
PORT=${port}
TTL_MIN=${ttl_min}
EXPIRES_EPOCH=${expires_epoch}
EOF
}

cmd_start() {
  local challenge=""
  local team=""
  local ttl_min=60
  local port=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --challenge) challenge="$(sanitize "${2:-}")"; shift 2 ;;
      --team) team="$(sanitize "${2:-}")"; shift 2 ;;
      --ttl-min) ttl_min="${2:-}"; shift 2 ;;
      --port) port="${2:-}"; shift 2 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done

  if [[ -z "$challenge" || -z "$team" ]]; then
    echo "--challenge and --team are required"
    exit 1
  fi

  if ! [[ "$ttl_min" =~ ^[0-9]+$ ]] || (( ttl_min < 1 || ttl_min > 240 )); then
    echo "--ttl-min must be between 1 and 240"
    exit 1
  fi

  local challenge_dir=""
  if ! challenge_dir=$(resolve_challenge_dir "$challenge"); then
    echo "Challenge folder not found for challenge=$challenge under /vagrant/challenges"
    exit 1
  fi

  if [[ ! -f "$challenge_dir/challenge.yml" ]]; then
    echo "challenge.yml missing in $challenge_dir"
    exit 1
  fi

  local challenge_type
  challenge_type=$(grep -E '^type:' "$challenge_dir/challenge.yml" | awk '{print $2}' | tr -d '\r' | head -1 || true)
  # Some CTFd challenge metadata may use non-docker type labels while still
  # providing a valid docker-compose runtime. Prefer runtime files over metadata.
  if [[ "$challenge_type" != "docker" && ! -f "$challenge_dir/docker-compose.yml" ]]; then
    echo "Challenge is not spawnable: missing docker-compose.yml"
    exit 1
  fi

  ensure_dirs

  local docker_compose=(sudo env HOME=/tmp DOCKER_CONFIG=/tmp/.docker docker compose)

  if [[ -z "$port" ]]; then
    port=$(find_free_port) || { echo "No free port found in ${PORT_MIN}-${PORT_MAX}"; exit 1; }
  fi

  if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < PORT_MIN || port > PORT_MAX )); then
    echo "--port must be in ${PORT_MIN}-${PORT_MAX}"
    exit 1
  fi

  if is_port_used "$port"; then
    echo "Port $port is already in use"
    exit 1
  fi

  local project
  project=$(project_for "$challenge" "$team")
  local instance_dir="$INSTANCES_ROOT/$project"
  local lease_file
  lease_file=$(lease_file_for "$challenge" "$team")

  if [[ -f "$lease_file" ]]; then
    # shellcheck disable=SC1090
    source "$lease_file"

    if sudo env HOME=/tmp DOCKER_CONFIG=/tmp/.docker docker compose -p "$PROJECT" -f "$INSTANCE_DIR/docker-compose.yml" ps --status running --services 2>/dev/null | grep -q .; then
      echo "Instance already running"
      echo "Project : $PROJECT"
      echo "URL     : http://192.168.56.10:${PORT}"
      echo "Expires : $(date -d "@${EXPIRES_EPOCH}" '+%Y-%m-%d %H:%M:%S')"
      return 0
    fi

    # Stale lease: cleanup and recreate.
    sudo rm -rf "$INSTANCE_DIR"
    sudo rm -f "$lease_file"
  fi

  sudo rm -rf "$instance_dir"
  sudo mkdir -p "$instance_dir"
  sudo cp -a "$challenge_dir/." "$instance_dir/"

  if [[ ! -f "$instance_dir/docker-compose.yml" ]]; then
    echo "docker-compose.yml missing in challenge"
    exit 1
  fi

  sudo sed -i -E "s/\"[0-9]+:5000\"/\"${port}:5000\"/" "$instance_dir/docker-compose.yml"
  sudo sed -i -E "s/^([[:space:]]*container_name:).*/\1 ${project}_challenge/" "$instance_dir/docker-compose.yml"

  "${docker_compose[@]}" -p "$project" -f "$instance_dir/docker-compose.yml" up -d --build

  local now expires_epoch
  now=$(date +%s)
  expires_epoch=$(( now + ttl_min * 60 ))

  write_lease "$lease_file" "$challenge" "$team" "$project" "$instance_dir" "$port" "$ttl_min" "$expires_epoch"

  echo "Instance started"
  echo "Project : $project"
  echo "URL     : http://192.168.56.10:${port}"
  echo "EXPIRE_EPOCH=${expires_epoch}"
  echo "Expires : $(date -d "@${expires_epoch}" '+%Y-%m-%d %H:%M:%S')"
}

cmd_stop() {
  local challenge=""
  local team=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --challenge) challenge="$(sanitize "${2:-}")"; shift 2 ;;
      --team) team="$(sanitize "${2:-}")"; shift 2 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done

  if [[ -z "$challenge" || -z "$team" ]]; then
    echo "--challenge and --team are required"
    exit 1
  fi

  local lease_file
  lease_file=$(lease_file_for "$challenge" "$team")

  if [[ ! -f "$lease_file" ]]; then
    local legacy_lease_file
    legacy_lease_file=$(lease_file_for "$(legacy_sanitize "$challenge")" "$team")
    if [[ -f "$legacy_lease_file" ]]; then
      lease_file="$legacy_lease_file"
    fi
  fi

  if [[ ! -f "$lease_file" ]]; then
    echo "No active lease for challenge=$challenge team=$team"
    return 1
  fi

  # shellcheck disable=SC1090
  source "$lease_file"

  sudo env HOME=/tmp DOCKER_CONFIG=/tmp/.docker docker compose -p "$PROJECT" -f "$INSTANCE_DIR/docker-compose.yml" down || true
  sudo rm -rf "$INSTANCE_DIR"
  sudo rm -f "$lease_file"

  echo "Instance stopped for challenge=$challenge team=$team"
}

cmd_extend() {
  local challenge=""
  local team=""
  local ttl_min=30

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --challenge) challenge="$(sanitize "${2:-}")"; shift 2 ;;
      --team) team="$(sanitize "${2:-}")"; shift 2 ;;
      --ttl-min) ttl_min="${2:-}"; shift 2 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done

  if [[ -z "$challenge" || -z "$team" ]]; then
    echo "--challenge and --team are required"
    exit 1
  fi

  if ! [[ "$ttl_min" =~ ^[0-9]+$ ]] || (( ttl_min < 1 || ttl_min > 240 )); then
    echo "--ttl-min must be between 1 and 240"
    exit 1
  fi

  local lease_file
  lease_file=$(lease_file_for "$challenge" "$team")

  if [[ ! -f "$lease_file" ]]; then
    local legacy_lease_file
    legacy_lease_file=$(lease_file_for "$(legacy_sanitize "$challenge")" "$team")
    if [[ -f "$legacy_lease_file" ]]; then
      lease_file="$legacy_lease_file"
    fi
  fi

  if [[ ! -f "$lease_file" ]]; then
    echo "No active lease for challenge=$challenge team=$team"
    return 1
  fi

  # shellcheck disable=SC1090
  source "$lease_file"

  local now
  local current_remaining
  local new_remaining
  local new_expires_epoch
  now=$(date +%s)
  current_remaining=$(( EXPIRES_EPOCH - now ))
  if (( current_remaining <= 0 )); then
    echo "Lease already expired for challenge=$challenge team=$team"
    return 1
  fi

  new_remaining=$(( current_remaining + ttl_min * 60 ))

  if (( new_remaining > 3600 )); then
    echo "Extension denied: total TTL cannot exceed 60 minutes"
    return 1
  fi

  new_expires_epoch=$(( now + new_remaining ))

  write_lease "$lease_file" "$CHALLENGE" "$TEAM" "$PROJECT" "$INSTANCE_DIR" "$PORT" "$(( (new_remaining + 59) / 60 ))" "$new_expires_epoch"

  echo "Instance extended"
  echo "Project : $PROJECT"
  echo "URL     : http://192.168.56.10:${PORT}"
  echo "EXPIRE_EPOCH=${new_expires_epoch}"
  echo "Expires : $(date -d "@${new_expires_epoch}" '+%Y-%m-%d %H:%M:%S')"
}

cmd_status() {
  ensure_dirs
  shopt -s nullglob
  local lease
  local now
  now=$(date +%s)

  for lease in "$LEASES_ROOT"/*.env; do
    # shellcheck disable=SC1090
    source "$lease"
    local remaining
    remaining=$(( EXPIRES_EPOCH - now ))
    local state="stopped"
    if sudo env HOME=/tmp DOCKER_CONFIG=/tmp/.docker docker compose -p "$PROJECT" -f "$INSTANCE_DIR/docker-compose.yml" ps --status running --services 2>/dev/null | grep -q .; then
      state="running"
    fi
    echo "project=$PROJECT challenge=$CHALLENGE team=$TEAM port=$PORT state=$state ttl_remaining_sec=$remaining"
  done
}

cmd_cleanup() {
  ensure_dirs
  shopt -s nullglob
  local now
  now=$(date +%s)

  local lease
  for lease in "$LEASES_ROOT"/*.env; do
    # shellcheck disable=SC1090
    source "$lease"
    if (( EXPIRES_EPOCH <= now )); then
      echo "Cleaning expired instance: $PROJECT"
      sudo env HOME=/tmp DOCKER_CONFIG=/tmp/.docker docker compose -p "$PROJECT" -f "$INSTANCE_DIR/docker-compose.yml" down || true
      sudo rm -rf "$INSTANCE_DIR"
      sudo rm -f "$lease"
    fi
  done
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  local command="$1"
  shift || true

  case "$command" in
    start) cmd_start "$@" ;;
    stop) cmd_stop "$@" ;;
    extend) cmd_extend "$@" ;;
    status) cmd_status ;;
    cleanup) cmd_cleanup ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
