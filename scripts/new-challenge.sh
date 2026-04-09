#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <challenge-name> [--family <web|osint|sandbox|reverse|pwn>] [--port <5001-5999>]"
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

NAME="$1"
shift || true
PORT=""
FAMILY="web"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --family)
      FAMILY="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "Invalid challenge name '$NAME'. Use lowercase, digits and hyphens only."
  exit 1
fi

if [[ ! "$FAMILY" =~ ^(web|osint|sandbox|reverse|pwn)$ ]]; then
  echo "Unsupported family '$FAMILY'."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_PATH="$REPO_ROOT/challenges/_templates/$FAMILY"
if [[ ! -d "$TEMPLATE_PATH" ]]; then
  TEMPLATE_PATH="$REPO_ROOT/challenges/_template"
fi
TARGET_PATH="$REPO_ROOT/challenges/$NAME"

if [[ ! -d "$TEMPLATE_PATH" ]]; then
  echo "Template folder not found: $TEMPLATE_PATH"
  exit 1
fi

if [[ -e "$TARGET_PATH" ]]; then
  echo "Target challenge already exists: $TARGET_PATH"
  exit 1
fi

CHALLENGE_TYPE=$(grep -E '^type:' "$TEMPLATE_PATH/challenge.yml" | awk '{print $2}' | tr -d '\r' || true)

if [[ "$CHALLENGE_TYPE" == "docker" && -z "$PORT" ]]; then
  MAX_PORT=$(grep -RhsE '^port:[[:space:]]*[0-9]+' "$REPO_ROOT/challenges"/*/challenge.yml 2>/dev/null | awk '{gsub(/[^0-9]/, "", $2); print $2}' | sort -n | tail -1 || true)
  if [[ -z "$MAX_PORT" ]]; then
    PORT=5001
  else
    PORT=$((MAX_PORT + 1))
  fi
fi

if [[ "$CHALLENGE_TYPE" == "docker" ]] && { ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 5001 || PORT > 5999 )); }; then
  echo "Port must be between 5001 and 5999. Provided: $PORT"
  exit 1
fi

cp -R "$TEMPLATE_PATH" "$TARGET_PATH"

CHALLENGE_YML="$TARGET_PATH/challenge.yml"
COMPOSE_YML="$TARGET_PATH/docker-compose.yml"
FLAG_NAME="${NAME//-/_}_flag"

sed -i.bak -E "s/^name:.*/name: ${NAME}/" "$CHALLENGE_YML"
sed -i.bak -E "s/^category:.*/category: ${FAMILY}/" "$CHALLENGE_YML"
sed -i.bak -E "s/^flag:.*/flag: CTF\{${FLAG_NAME}\}/" "$CHALLENGE_YML"
rm -f "$CHALLENGE_YML.bak"

if [[ "$CHALLENGE_TYPE" == "docker" ]]; then
  sed -i.bak -E "s/^port:[[:space:]]*[0-9]+[[:space:]]*$/port: ${PORT}/" "$CHALLENGE_YML"
  rm -f "$CHALLENGE_YML.bak"

  if [[ -f "$COMPOSE_YML" ]]; then
    sed -i.bak -E "s/^([[:space:]]*container_name:).*/\1 ${NAME}/" "$COMPOSE_YML"
    sed -i.bak -E "s/\"[0-9]+:5000\"/\"${PORT}:5000\"/" "$COMPOSE_YML"
    rm -f "$COMPOSE_YML.bak"
  fi
fi

echo "Challenge created: $TARGET_PATH"
if [[ "$FAMILY" == "osint" ]]; then
  sed -i.bak -E "s|^connection_info:.*|connection_info: http://192.168.56.10/osint/$NAME/resources/|" "$CHALLENGE_YML"
  rm -f "$CHALLENGE_YML.bak"
  echo "Lien d'accès statique : http://192.168.56.10/osint/$NAME/resources/"
fi
if [[ "$CHALLENGE_TYPE" == "docker" ]]; then
  echo "Assigned port: $PORT"
fi
echo "Next step: ./scripts/validate-challenge.sh challenges/$NAME"
