"""Git pre-push entry. Read exact remote SHA from native Git hook stdin."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
COMMAND = ['bash', 'scripts/pre_push.sh']


def outgoing_base(lines, head):
    updates = [line.split() for line in lines if line.strip()]
    if len(updates) != 1 or len(updates[0]) != 4:
        raise ValueError("Expected exactly one main update from Git pre-push stdin")
    _, local_sha, remote_ref, remote_sha = updates[0]
    if remote_ref != "refs/heads/main":
        raise ValueError("This repository's configured publication target is main")
    if not SHA.fullmatch(local_sha) or not SHA.fullmatch(remote_sha):
        raise ValueError("Git supplied an invalid immutable push SHA")
    if local_sha != head:
        raise ValueError("The outgoing commit must match the checked-out HEAD")
    return remote_sha


def main():
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    base = outgoing_base(sys.stdin, head)
    subprocess.run([*COMMAND, "--base", base], cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
