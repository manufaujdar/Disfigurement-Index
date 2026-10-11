"""Prepare exact committed review scopes. A model call requires explicit --execute."""
import argparse
import json
import re
import subprocess


def review_result(output, code):
    events = [json.loads(line) for line in output.splitlines() if line.strip()]
    if not all(isinstance(event, dict) for event in events):
        raise ValueError("review events must be JSON objects")
    findings = [e for e in events if e.get("type") == "finding"]
    complete = [e for e in events if e.get("type") == "complete"]
    failed = any(e.get("type") == "error" for e in events)
    result = complete[-1] if complete else {}
    incomplete = code != 0 or failed or not complete or result.get("status") not in ("review_completed", "review_skipped") or result.get("outcome") == "failed" or result.get("unreviewedFileCount", 0) != 0
    skipped = result.get("status") == "review_skipped"
    severities = {}
    for finding in findings:
        severity = finding.get("severity", "unknown")
        severities[severity] = severities.get(severity, 0) + 1
    status = "incomplete" if incomplete else "skipped" if skipped else "completed"
    return {"status": status, "findings": len(findings), "severities": severities, "reused": bool(result.get("reused"))}, 1 if incomplete or skipped else 0


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--execute", action="store_true", help="Explicit external review; requires authenticated CLI and agreed source scope")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", args.base) or set(args.base) == {"0"}:
        parser.error("base must be an existing nonzero commit SHA")
    head = git("rev-parse", "HEAD")
    if args.head != "HEAD" and (not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", args.head) or args.head.lower() != head):
        parser.error("head must match this checkout's exact commit")
    subprocess.run(["git", "merge-base", "--is-ancestor", args.base, head], check=True)
    if git("status", "--porcelain", "--untracked-files=no"):
        parser.error("review requires a clean tracked checkout of the outgoing commit")
    paths = git("diff", "--name-only", args.base, head).splitlines()
    print(json.dumps({"status": "prepared_not_reviewed", "base": args.base, "head": head, "changed_file_count": len(paths)}), flush=True)
    if not args.execute:
        return 0
    if not paths:
        parser.error("empty scope is not a completed review")
    run = subprocess.run(["coderabbit", "review", "--committed", "--base-commit", args.base, "--agent"], capture_output=True, text=True, timeout=1800, check=False)
    try:
        result, code = review_result(run.stdout, run.returncode)
    except (ValueError, TypeError, KeyError):
        print(json.dumps({"status": "incomplete", "reason": "invalid review output"}))
        return 1
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
