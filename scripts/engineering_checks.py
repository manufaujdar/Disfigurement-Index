"""Local/push checks. No writes, remote reviewers, or credential validation."""
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
ENGINEERING_DOCS = ("README.md", "CONTRIBUTING.md", "QUALITY.md", "TOOLING.md", "CHANGELOG.md")


def call(argv, **kwargs):
    return subprocess.run(argv, cwd=ROOT, check=True, **kwargs)


def git(*args):
    return call(["git", *args], capture_output=True, text=True).stdout.strip()


def resolve(ref):
    value = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    if not SHA.fullmatch(value):
        raise ValueError("Expected an immutable commit SHA")
    return value


def document_errors(path):
    text = path.read_text(encoding="utf-8")
    errors = []
    # Markdown syntax/formatting is handled by markdownlint; only file links here.
    text = re.sub(r"(?ms)^\s*```.*?^\s*```\s*$", "", text)
    targets = re.findall(r"!?\[[^\]\n]*\]\((<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)", text)
    targets += re.findall(r"(?m)^\s*\[[^]]+\]:\s*(\S+)", text)
    for raw in targets:
        target = unquote(raw.strip("<>"))
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path or url.path.startswith("/"):
            continue
        destination = (path.parent / url.path).resolve()
        # External workspace references are deliberately outside this repo's check.
        if not destination.is_relative_to(ROOT):
            continue
        if not destination.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing relative link {url.path}")
    return errors


def changed_docs(base):
    paths = git("ls-files", "-z").split("\0") if base is None else git("diff", "--name-only", "--diff-filter=ACMR", "-z", base, "--").split("\0")
    paths += git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({p for p in paths if p.endswith(".md") and (p in ENGINEERING_DOCS or p.startswith("docs/")) and (ROOT / p).is_file()})


def check_docs(paths):
    errors = [error for name in paths for error in document_errors(ROOT / name)]
    if errors:
        raise ValueError("\n".join(errors))
    if paths:
        tool = os.environ.get("MARKDOWNLINT", str(ROOT / "tools/docs-tools/node_modules/.bin/markdownlint"))
        call([tool, "--config", ".markdownlint.json", *paths])
        call(["lychee", "--offline", "--no-progress", *paths])
    print(f"Engineering docs: {len(paths)} changed files; offline relative links checked")


def run(base, working=False):
    head = resolve("HEAD")
    if not working and git("status", "--porcelain=v1"):
        raise ValueError("Commit intended changes before pre-push checks; working tree must be clean")
    if base == "0" * 40:
        # Initial push: explicitly check all reachable history, never silently skip.
        base = None
        secret_range = head
    else:
        base = resolve(base)
        call(["git", "merge-base", "--is-ancestor", base, head])
        secret_range = f"{base}..{head}"
    check_docs(changed_docs(base))
    for tool in ("actionlint", "zizmor", "betterleaks", "lychee"):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}; see TOOLING.md for pinned installation")
    call(["actionlint", "-shellcheck=", "-pyflakes="])
    call(["zizmor", "--offline", "--no-progress", ".github/workflows"])
    if not working:
        call(["betterleaks", "git", "--redact=100", "--no-banner", "--exit-code", "1", "--log-opts", secret_range, "."])
    else:
        print("Working-tree mode: commit-range secrets run after commit; staged secret gate remains required")
    if resolve("HEAD") != head:
        raise ValueError("HEAD changed during checks; rerun for the actual outgoing commit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Verified ancestor commit/ref for the outgoing range")
    parser.add_argument("--working", action="store_true", help="Pre-commit verification; does not certify the outgoing secret range")
    options = parser.parse_args()
    run(options.base, options.working)
