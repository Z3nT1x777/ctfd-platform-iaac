#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <challenge-path-relative-to-repo>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHALLENGE_PATH="$REPO_ROOT/$1"

if [[ ! -d "$CHALLENGE_PATH" ]]; then
  echo "Challenge path not found: $CHALLENGE_PATH"
  exit 1
fi

required_files=(
  Dockerfile
  app.py
  flag.txt
  requirements.txt
  docker-compose.yml
  challenge.yml
)

errors=()
for file in "${required_files[@]}"; do
  if [[ ! -f "$CHALLENGE_PATH/$file" ]]; then
    errors+=("Missing required file: $file")
  fi
done

CHALLENGE_YML="$CHALLENGE_PATH/challenge.yml"
COMPOSE_YML="$CHALLENGE_PATH/docker-compose.yml"

if [[ -f "$CHALLENGE_YML" ]]; then
  required_keys=(name category value type description flag port)
  for key in "${required_keys[@]}"; do
    if ! grep -qE "^${key}:" "$CHALLENGE_YML"; then
      errors+=("challenge.yml missing key: $key")
    fi
  done

  port_line=$(grep -E '^port:[[:space:]]*[0-9]+' "$CHALLENGE_YML" | head -1 || true)
  if [[ -z "$port_line" ]]; then
    errors+=("challenge.yml missing numeric port")
  else
    port=$(echo "$port_line" | awk '{print $2}')
    if (( port < 5001 || port > 5999 )); then
      errors+=("Port out of expected range (5001-5999): $port")
    fi

    if [[ -f "$COMPOSE_YML" ]] && ! grep -q "\"${port}:5000\"" "$COMPOSE_YML"; then
      errors+=("docker-compose.yml does not expose expected port mapping: ${port}:5000")
    fi
  fi
fi

if (( ${#errors[@]} > 0 )); then
  echo "Validation FAILED:"
  for err in "${errors[@]}"; do
    echo " - $err"
  done
  exit 1
fi

echo "Validation OK"
echo "Challenge path: $1"
