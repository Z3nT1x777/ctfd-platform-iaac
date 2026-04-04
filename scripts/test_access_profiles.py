#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "scripts" / "ctfd-orchestrator-plugin"
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from access_profiles import build_access_methods, load_access_hint_from_dir


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_web_example() -> None:
    challenge_dir = ROOT / "challenges" / "web" / "simple-login"
    hints = load_access_hint_from_dir(challenge_dir)
    methods = build_access_methods(
        challenge_name="Simple Login",
        challenge_dir=challenge_dir,
        url="http://192.168.56.10:5001",
        port=5001,
        stdout="Instance started",
    )

    assert_true(hints["mode"] == "web", "simple-login should declare web mode")
    assert_true(any(m["type"] == "web" for m in methods), "web example should render a web method")
    assert_true(all(m["type"] != "ssh" for m in methods), "web example should not render SSH commands")


def test_ssh_example() -> None:
    challenge_dir = ROOT / "challenges" / "sandbox" / "ssh-lab"
    hints = load_access_hint_from_dir(challenge_dir)
    methods = build_access_methods(
        challenge_name="SSH Lab",
        challenge_dir=challenge_dir,
        port=5003,
        stdout="SSH service ready",
    )

    assert_true(hints["mode"] == "ssh", "ssh-lab should declare ssh mode")
    ssh_methods = [m for m in methods if m["type"] == "ssh"]
    assert_true(bool(ssh_methods), "ssh example should render SSH commands")
    assert_true("-p 5003" in ssh_methods[0]["linux"], "SSH command should use the host port")
    assert_true(all(m["type"] != "web" for m in methods), "ssh example should not render a web button")


def test_instruction_example() -> None:
    challenge_dir = ROOT / "challenges" / "osint" / "eiffel-shadow"
    hints = load_access_hint_from_dir(challenge_dir)
    methods = build_access_methods(
        challenge_name="Eiffel Shadow",
        challenge_dir=challenge_dir,
        stdout="Static instruction challenge",
    )

    assert_true(hints["mode"] == "instruction", "osint example should declare instruction mode")
    assert_true(any(m["type"] == "instruction" for m in methods), "instruction example should render instructions")
    assert_true(all(m["type"] != "web" for m in methods), "instruction example should not render a web button")
    assert_true(all(m["type"] != "ssh" for m in methods), "instruction example should not render SSH commands")


def main() -> int:
    test_web_example()
    test_ssh_example()
    test_instruction_example()
    print("Access profile tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
