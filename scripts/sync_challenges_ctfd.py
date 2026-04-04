#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHALLENGES_ROOT = REPO_ROOT / "challenges"


@dataclass
class ChallengeSpec:
    path: Path
    name: str
    category: str
    value: int
    challenge_type: str
    description: str
    flag: str
    port: int | None


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_challenge_yml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = 0

    while idx < len(lines):
        raw = lines[idx]
        line = raw.strip()

        if not line or line.startswith("#"):
            idx += 1
            continue

        if line.startswith("description:"):
            if line.endswith("|"):
                block: list[str] = []
                idx += 1
                while idx < len(lines):
                    nxt = lines[idx]
                    if nxt.startswith("  "):
                        block.append(nxt[2:])
                        idx += 1
                        continue
                    if nxt.strip() == "":
                        block.append("")
                        idx += 1
                        continue
                    break
                data["description"] = "\n".join(block).strip()
                continue

            _, value = line.split(":", 1)
            data["description"] = _strip_quotes(value)
            idx += 1
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = _strip_quotes(value)

        idx += 1

    return data


def discover_challenges(challenges_root: Path) -> list[Path]:
    challenge_dirs: list[Path] = []
    for yml in challenges_root.rglob("challenge.yml"):
        rel_parts = yml.relative_to(challenges_root).parts
        if any(part.startswith("_") for part in rel_parts):
            continue
        challenge_dirs.append(yml.parent)
    return sorted(challenge_dirs)


def build_spec(challenge_dir: Path) -> ChallengeSpec:
    yml_path = challenge_dir / "challenge.yml"
    raw = parse_challenge_yml(yml_path)

    name = str(raw.get("name", "")).strip()
    category = str(raw.get("category", "misc")).strip() or "misc"
    value = int(str(raw.get("value", "100")).strip() or "100")
    challenge_type = str(raw.get("type", "docker")).strip() or "docker"
    description = str(raw.get("description", "")).strip()
    flag = str(raw.get("flag", "")).strip()

    if not flag:
        flag_file = challenge_dir / "flag.txt"
        if flag_file.exists():
            flag = flag_file.read_text(encoding="utf-8").strip().splitlines()[0].strip()

    port: int | None = None
    port_raw = str(raw.get("port", "")).strip()
    if port_raw.isdigit():
        port = int(port_raw)

    if not name:
        raise ValueError(f"Missing 'name' in {yml_path}")
    if not flag:
        raise ValueError(f"Missing flag in {yml_path} and flag.txt")

    return ChallengeSpec(
        path=challenge_dir,
        name=name,
        category=category,
        value=value,
        challenge_type=challenge_type,
        description=description,
        flag=flag,
        port=port,
    )


def api_request(
    session: requests.Session,
    method: str,
    base_url: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{endpoint}"
    resp = session.request(method=method, url=url, json=payload, timeout=20)

    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data = resp.json()
    else:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise RuntimeError(
            f"{method} {endpoint} failed ({resp.status_code}): {json.dumps(data)}"
        )

    return data


def get_existing_challenges(session: requests.Session, base_url: str) -> dict[str, dict[str, Any]]:
    data = api_request(session, "GET", base_url, "/api/v1/challenges")
    items = data.get("data", [])
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        name = str(item.get("name", "")).strip()
        if name:
            result[name] = item
    return result


def upsert_flag(
    session: requests.Session,
    base_url: str,
    challenge_id: int,
    flag_value: str,
    dry_run: bool,
) -> None:
    payload = {
        "challenge_id": challenge_id,
        "content": flag_value,
        "type": "static",
        "data": "case_insensitive",
    }

    if dry_run:
        print(f"[dry-run] upsert flag for challenge_id={challenge_id}")
        return

    # CTFd usually supports listing flags with filter by challenge_id.
    existing_data = api_request(
        session,
        "GET",
        base_url,
        f"/api/v1/flags?challenge_id={challenge_id}",
    )
    existing_flags = existing_data.get("data", [])

    if existing_flags:
        first_id = int(existing_flags[0]["id"])
        api_request(session, "PATCH", base_url, f"/api/v1/flags/{first_id}", payload)
        # Keep one canonical flag to avoid duplicates.
        for extra in existing_flags[1:]:
            api_request(session, "DELETE", base_url, f"/api/v1/flags/{int(extra['id'])}")
    else:
        api_request(session, "POST", base_url, "/api/v1/flags", payload)


def sync_challenge(
    session: requests.Session,
    base_url: str,
    spec: ChallengeSpec,
    existing: dict[str, dict[str, Any]],
    state: str,
    instance_base_url: str | None,
    dry_run: bool,
) -> str:
    connection_info = ""
    if spec.port is not None and instance_base_url:
        connection_info = f"{instance_base_url.rstrip('/')}:{spec.port}"

    challenge_payload: dict[str, Any] = {
        "name": spec.name,
        "category": spec.category,
        "description": spec.description,
        "value": spec.value,
        "type": "standard",
        "state": state,
        "connection_info": connection_info,
    }

    action = "create"
    challenge_id: int
    if spec.name in existing:
        action = "update"
        challenge_id = int(existing[spec.name]["id"])
    else:
        challenge_id = -1

    if dry_run:
        print(f"[dry-run] {action} challenge '{spec.name}' ({spec.path})")
        return action

    if action == "create":
        created = api_request(session, "POST", base_url, "/api/v1/challenges", challenge_payload)
        challenge_id = int(created["data"]["id"])
    else:
        api_request(
            session,
            "PATCH",
            base_url,
            f"/api/v1/challenges/{challenge_id}",
            challenge_payload,
        )

    upsert_flag(
        session=session,
        base_url=base_url,
        challenge_id=challenge_id,
        flag_value=spec.flag,
        dry_run=dry_run,
    )

    return action


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync challenge.yml files to CTFd via API (create/update + flags)."
    )
    parser.add_argument(
        "--ctfd-url",
        default=os.environ.get("CTFD_URL", "http://127.0.0.1"),
        help="Base URL of CTFd, e.g. http://127.0.0.1 or http://192.168.56.10",
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("CTFD_API_TOKEN", ""),
        help="CTFd API token (admin token recommended).",
    )
    parser.add_argument(
        "--challenges-root",
        default=str(DEFAULT_CHALLENGES_ROOT),
        help="Path to challenges root directory.",
    )
    parser.add_argument(
        "--state",
        choices=["visible", "hidden"],
        default="visible",
        help="CTFd challenge state after sync.",
    )
    parser.add_argument(
        "--instance-base-url",
        default=os.environ.get("CTFD_INSTANCE_BASE_URL", "http://192.168.56.10"),
        help="Base URL used to populate connection_info when challenge port is present.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing to CTFd.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_token:
        print("ERROR: missing API token. Provide --api-token or CTFD_API_TOKEN.")
        return 1

    challenges_root = Path(args.challenges_root).resolve()
    if not challenges_root.exists():
        print(f"ERROR: challenges root not found: {challenges_root}")
        return 1

    challenge_dirs = discover_challenges(challenges_root)
    if not challenge_dirs:
        print(f"ERROR: no challenge.yml found under {challenges_root}")
        return 1

    specs: list[ChallengeSpec] = []
    for challenge_dir in challenge_dirs:
        try:
            specs.append(build_spec(challenge_dir))
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Token {args.api_token}",
            "Content-Type": "application/json",
        }
    )

    try:
        existing = get_existing_challenges(session, args.ctfd_url)
    except Exception as exc:
        print(f"ERROR: unable to fetch existing CTFd challenges: {exc}")
        return 1

    created = 0
    updated = 0

    for spec in specs:
        try:
            action = sync_challenge(
                session=session,
                base_url=args.ctfd_url,
                spec=spec,
                existing=existing,
                state=args.state,
                instance_base_url=args.instance_base_url,
                dry_run=args.dry_run,
            )
            if action == "create":
                created += 1
            else:
                updated += 1
            print(f"OK: {action} -> {spec.name}")
        except Exception as exc:
            print(f"ERROR syncing {spec.name}: {exc}")
            return 1

    print(
        f"Done. total={len(specs)} created={created} updated={updated} dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
