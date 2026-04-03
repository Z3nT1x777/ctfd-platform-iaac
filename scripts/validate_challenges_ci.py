#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
CHALLENGES_ROOT = REPO_ROOT / "challenges"

REQUIRED_KEYS = ["name", "category", "value", "type", "description", "flag"]
DOCKER_REQUIRED_FILES = [
    "Dockerfile",
    "app.py",
    "flag.txt",
    "requirements.txt",
    "docker-compose.yml",
    "challenge.yml",
]
PORT_MIN = 5001
PORT_MAX = 5999


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_simple_yaml(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def find_challenge_dirs(root: Path) -> List[Path]:
    challenge_dirs: List[Path] = []
    for yml in root.rglob("challenge.yml"):
        if any(part.startswith("_") for part in yml.parent.parts):
            continue
        challenge_dirs.append(yml.parent)
    return sorted(set(challenge_dirs))


def validate_challenge(path: Path, used_ports: Dict[int, Path]) -> List[str]:
    errors: List[str] = []
    rel = path.relative_to(REPO_ROOT)

    challenge_yml = path / "challenge.yml"
    if not challenge_yml.exists():
        return [f"{rel}: missing challenge.yml"]

    data = parse_simple_yaml(challenge_yml)

    for key in REQUIRED_KEYS:
        if key not in data or not data[key]:
            errors.append(f"{rel}: challenge.yml missing key '{key}'")

    value = data.get("value", "")
    if value and not value.isdigit():
        errors.append(f"{rel}: value must be an integer")

    flag = data.get("flag", "")
    if flag and not re.fullmatch(r"CTF\{[^{}]+\}", flag):
        errors.append(f"{rel}: flag must match CTF{{...}}")

    challenge_type = data.get("type", "")
    if challenge_type == "docker":
        for filename in DOCKER_REQUIRED_FILES:
            if not (path / filename).exists():
                errors.append(f"{rel}: missing required file '{filename}' for docker challenge")

        port_str = data.get("port", "")
        if not port_str or not port_str.isdigit():
            errors.append(f"{rel}: docker challenge must define numeric port")
        else:
            port = int(port_str)
            if port < PORT_MIN or port > PORT_MAX:
                errors.append(f"{rel}: port must be in range {PORT_MIN}-{PORT_MAX}, got {port}")
            elif port in used_ports:
                errors.append(
                    f"{rel}: port {port} already used by {used_ports[port].relative_to(REPO_ROOT)}"
                )
            else:
                used_ports[port] = path

            compose_file = path / "docker-compose.yml"
            if compose_file.exists():
                compose = read_text(compose_file)
                expected_mapping = f'"{port}:5000"'
                if expected_mapping not in compose:
                    errors.append(
                        f"{rel}: docker-compose.yml must expose {expected_mapping}"
                    )

    return errors


def main() -> int:
    if not CHALLENGES_ROOT.exists():
        print("ERROR: challenges directory not found")
        return 1

    challenge_dirs = find_challenge_dirs(CHALLENGES_ROOT)
    if not challenge_dirs:
        print("ERROR: no challenge.yml found under challenges/")
        return 1

    all_errors: List[str] = []
    used_ports: Dict[int, Path] = {}

    for challenge_dir in challenge_dirs:
        all_errors.extend(validate_challenge(challenge_dir, used_ports))

    if all_errors:
        print("Challenge validation failed:")
        for error in all_errors:
            print(f" - {error}")
        return 1

    print("Challenge validation succeeded")
    print(f"Validated {len(challenge_dirs)} challenge(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
