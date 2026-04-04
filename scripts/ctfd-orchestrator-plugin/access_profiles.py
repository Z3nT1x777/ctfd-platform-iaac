from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

DEFAULT_PLAYER_HOST = "192.168.56.10"
DEFAULT_SSH_USER = "ctf"


def normalize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", (value or "").strip().lower().replace(" ", "-"))


def parse_simple_challenge_yaml(yaml_text: str) -> Dict[str, str]:
    """Parse the small YAML subset used by challenge metadata files.

    The repo intentionally keeps challenge.yml simple enough that a tiny parser
    is sufficient for access-profile inference and tests.
    """
    result: Dict[str, str] = {}
    lines = yaml_text.splitlines()
    index = 0

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        index += 1

        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value in {"|", ">"}:
            block: List[str] = []
            base_indent = None
            while index < len(lines):
                candidate = lines[index]
                if not candidate.strip():
                    block.append("")
                    index += 1
                    continue

                indent = len(candidate) - len(candidate.lstrip(" "))
                if base_indent is None:
                    base_indent = indent
                if indent < (base_indent or 0):
                    break

                block.append(candidate[base_indent:])
                index += 1

            result[key] = "\n".join(block).strip()
            continue

        if value:
            result[key] = value.strip().strip('"\'')

    return result


def load_access_hint_from_dir(challenge_dir: Union[str, Path]) -> Dict[str, str]:
    challenge_path = Path(challenge_dir)
    yml_path = challenge_path / "challenge.yml"
    if not yml_path.exists():
        return {"mode": "auto", "ssh_user": "", "instructions": "", "container_port": ""}

    try:
        yml_text = yml_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {"mode": "auto", "ssh_user": "", "instructions": "", "container_port": ""}

    metadata = parse_simple_challenge_yaml(yml_text)
    mode = (metadata.get("connection_mode") or metadata.get("access_mode") or "auto").strip().lower()
    ssh_user = metadata.get("ssh_user", "").strip()
    instructions = metadata.get("access_instructions", "").strip()
    container_port = metadata.get("container_port", metadata.get("internal_port", "")).strip()

    return {
        "mode": mode,
        "ssh_user": ssh_user,
        "instructions": instructions,
        "container_port": container_port,
        "type": metadata.get("type", "").strip().lower(),
    }


def build_access_methods(
    *,
    challenge_name: str,
    challenge_dir: Union[str, Path],
    connection_info: str = "",
    url: str = "",
    port: Any = 0,
    stdout: str = "",
    player_host: str = DEFAULT_PLAYER_HOST,
    default_ssh_user: str = DEFAULT_SSH_USER,
) -> List[Dict[str, str]]:
    """Build a normalized access-method list for launch rendering.

    Supported method types:
    - web
    - ssh
    - instruction
    """
    hints = load_access_hint_from_dir(challenge_dir)
    mode = hints.get("mode", "auto") or "auto"
    ssh_user = hints.get("ssh_user") or default_ssh_user
    challenge_type = hints.get("type", "")
    raw_note = (hints.get("instructions") or connection_info or "").strip()
    low_blob = f"{connection_info}\n{stdout}".lower()

    try:
        port_num = int(port or 0)
    except Exception:
        port_num = 0

    container_port = 0
    raw_container_port = hints.get("container_port", "")
    if raw_container_port.isdigit():
        container_port = int(raw_container_port)

    web_url = str(url or "").strip()
    if not web_url and port_num > 0 and mode in {"web", "auto"}:
        web_url = f"http://{player_host}:{port_num}"

    methods: List[Dict[str, str]] = []

    def add_web(target_url: str) -> None:
        if target_url and not any(m.get("type") == "web" for m in methods):
            methods.append({"type": "web", "label": "Open in Browser", "value": target_url})

    def add_ssh(target_port: int) -> None:
        if target_port <= 0 or any(m.get("type") == "ssh" for m in methods):
            return
        methods.append(
            {
                "type": "ssh",
                "label": "SSH Command",
                "linux": f"ssh {ssh_user}@{player_host} -p {target_port}",
                "windows": f"ssh {ssh_user}@{player_host} -p {target_port}",
            }
        )

    def add_instruction(note: str) -> None:
        note_text = (note or "").strip()
        if note_text and not any(m.get("type") == "instruction" for m in methods):
            methods.append({"type": "instruction", "label": "Instructions", "value": note_text})

    def looks_like_ssh_context() -> bool:
        return (
            container_port == 22
            or "ssh" in low_blob
            or "ssh" in (challenge_name or "").lower()
            or "ssh" in (challenge_type or "")
        )

    if mode == "web":
        add_web(web_url)
        if not methods:
            add_instruction(raw_note or "Web challenge launched, but no URL was resolved.")
    elif mode == "ssh":
        add_ssh(port_num)
        if not methods:
            add_instruction(raw_note or "SSH challenge: runtime metadata is missing host/port.")
    elif mode == "instruction":
        add_instruction(raw_note or "Follow the challenge instructions in CTFd.")
    else:
        if looks_like_ssh_context():
            add_ssh(port_num)
            if not methods:
                add_instruction(raw_note or "SSH challenge: use your terminal to connect.")
        elif web_url:
            add_web(web_url)
        else:
            add_instruction(raw_note or "Instance launched. Check the challenge description for access details.")

    return methods
