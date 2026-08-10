#!/usr/bin/env python3
"""Local-first frontend review agent for the Disfigurement Index website.

The default workflow is deterministic and does not call an external model.
The prompt command prepares a bounded review brief for a human-selected agent.
It deliberately never uploads repository files or edits source code.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_ROOT = Path(__file__).resolve().parents[2]
HTML_FILES = ("index.html", "image-analysis.html", "about.html", "forum.html", "author.html", "privacy.html")


@dataclass(frozen=True)
class Finding:
    severity: str
    area: str
    title: str
    detail: str
    next_action: str


@dataclass(frozen=True)
class AgentProfile:
    name: str
    kind: str
    strengths: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    source: str


class _HtmlAuditParser(HTMLParser):
    COPY_BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "summary", "li"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.ids: list[str] = []
        self.links: list[str] = []
        self.aria_controls: list[str] = []
        self.buttons = 0
        self.inputs = 0
        self.labels = 0
        self.forms = 0
        self.h1 = 0
        self.main = 0
        self.current = 0
        self.images_without_alt = 0
        self.live_regions = 0
        self.has_lang = False
        self.has_title = False
        self.has_viewport = False
        self.has_skip_link = False
        self.visible_copy_blocks = 0
        self.visible_text_fragments = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag)
        attributes = dict(attrs)
        if tag == "html" and attributes.get("lang"):
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        if tag == "meta" and attributes.get("name") == "viewport":
            self.has_viewport = True
        if tag == "main":
            self.main += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "form":
            self.forms += 1
        if tag == "button":
            self.buttons += 1
        if tag in {"input", "select", "textarea"}:
            self.inputs += 1
        if tag == "label":
            self.labels += 1
        if tag == "img" and "alt" not in attributes:
            self.images_without_alt += 1
        if tag == "a" and attributes.get("href") == "#main":
            self.has_skip_link = True
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))
        if attributes.get("id"):
            self.ids.append(str(attributes["id"]))
        if attributes.get("aria-controls"):
            self.aria_controls.append(str(attributes["aria-controls"]))
        if attributes.get("aria-current") == "page":
            self.current += 1
        if attributes.get("aria-live") or attributes.get("role") == "status":
            self.live_regions += 1
        if tag in self.COPY_BLOCK_TAGS and "script" not in self.stack and "style" not in self.stack:
            self.visible_copy_blocks += 1

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in {"script", "style", "option"} for tag in self.stack):
            return
        if " ".join(data.split()):
            self.visible_text_fragments += 1


def _read_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for name in (*HTML_FILES, "README.md", "assets/css/styles.css", "assets/js/app.js"):
        path = root / name
        if path.exists():
            files[name] = path.read_text(encoding="utf-8")
    return files


def _local_link_errors(root: Path, links: list[str]) -> list[str]:
    errors: list[str] = []
    for href in links:
        parsed = urlparse(href)
        if parsed.scheme or href.startswith("#") or href.startswith("mailto:"):
            continue
        target_name = href.split("#", 1)[0]
        if not target_name:
            continue
        if not (root / target_name).exists():
            errors.append(href)
    return errors


def audit_frontend(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    files = _read_files(root)
    css = files.get("assets/css/styles.css", "")
    javascript = files.get("assets/js/app.js", "")
    readme = files.get("README.md", "")
    findings: list[Finding] = []
    page_summaries: dict[str, dict[str, Any]] = {}

    for name in HTML_FILES:
        html = files.get(name, "")
        parser = _HtmlAuditParser()
        parser.feed(html)
        duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        missing_controls = [value for value in parser.aria_controls if value not in parser.ids]
        broken_links = _local_link_errors(root, parser.links)
        page_summaries[name] = {
            "h1": parser.h1,
            "main": parser.main,
            "forms": parser.forms,
            "buttons": parser.buttons,
            "inputs": parser.inputs,
            "labels": parser.labels,
            "ariaCurrentPageLinks": parser.current,
            "liveRegions": parser.live_regions,
            "visibleCopyBlocks": parser.visible_copy_blocks,
            "visibleTextFragments": parser.visible_text_fragments,
        }

        if not parser.has_lang:
            findings.append(Finding("high", "accessibility", f"{name} missing language", "The html element does not declare a language.", "Add lang=\"en\" to the html element."))
        if not parser.has_title:
            findings.append(Finding("high", "accessibility", f"{name} missing title", "The page has no document title.", "Add a descriptive title element."))
        if not parser.has_viewport:
            findings.append(Finding("medium", "responsive", f"{name} missing viewport", "Mobile browsers may render at desktop width.", "Add a responsive viewport meta tag."))
        if not parser.has_skip_link:
            findings.append(Finding("medium", "accessibility", f"{name} missing skip link", "Keyboard users cannot jump past repeated navigation.", "Add a visible-on-focus skip link to main content."))
        if parser.main != 1:
            findings.append(Finding("high", "accessibility", f"{name} main landmark issue", f"Expected one main landmark, found {parser.main}.", "Keep one main element per page."))
        if parser.h1 != 1:
            findings.append(Finding("medium", "accessibility", f"{name} heading issue", f"Expected one h1, found {parser.h1}.", "Keep one primary page heading."))
        if parser.current != 1:
            findings.append(Finding("medium", "navigation", f"{name} current page marker issue", f"Expected one aria-current page link, found {parser.current}.", "Mark exactly one active navigation link."))
        if duplicate_ids:
            findings.append(Finding("high", "accessibility", f"{name} duplicate ids", ", ".join(duplicate_ids), "Ensure ids are unique."))
        if missing_controls:
            findings.append(Finding("high", "accessibility", f"{name} broken aria-controls", ", ".join(missing_controls), "Point aria-controls to an existing id."))
        if broken_links:
            findings.append(Finding("high", "navigation", f"{name} broken local links", ", ".join(broken_links), "Fix or remove broken local links."))
        if parser.images_without_alt:
            findings.append(Finding("medium", "accessibility", f"{name} image alt issue", f"{parser.images_without_alt} image element(s) lack alt text.", "Add alt text or mark decorative images in CSS/ARIA."))
        if parser.forms and parser.labels < parser.inputs:
            findings.append(Finding("medium", "accessibility", f"{name} form label coverage", f"{parser.inputs} controls and {parser.labels} labels detected.", "Make every control programmatically labelled."))

    if "@media" not in css:
        findings.append(Finding("medium", "responsive", "No responsive CSS found", "The stylesheet has no breakpoint.", "Add mobile and tablet breakpoints."))
    if ":focus-visible" not in css:
        findings.append(Finding("medium", "accessibility", "Focus state is not explicit", "Keyboard users need a visible focus indicator.", "Add :focus-visible styles."))
    if "innerHTML" in javascript and "escapeHtml" not in javascript:
        findings.append(Finding("high", "security", "Dynamic HTML needs escaping", "The app renders dynamic HTML without an obvious escaping helper.", "Use textContent or escape dynamic values."))
    if "localStorage" not in javascript and "SQLite" not in readme:
        findings.append(Finding("medium", "privacy", "Persistence is under-documented", "Local persistence behavior is unclear.", "Document browser and SQLite storage boundaries."))
    lower_readme = readme.lower()
    if "clinical validation" not in lower_readme or "diagnostic" not in lower_readme:
        findings.append(Finding("high", "clinical-boundary", "Research boundary is under-documented", "The README should clearly reject clinical validation or diagnostic status.", "Add research-only and validation-needed language."))

    scores = {"accessibility": 9, "navigation": 9, "responsive": 8, "security": 8, "privacy": 8, "clinical-boundary": 8, "maintainability": 8}
    deductions = {"high": 3, "medium": 2, "low": 1}
    for finding in findings:
        if finding.area in scores:
            scores[finding.area] = max(0, scores[finding.area] - deductions[finding.severity])

    return {
        "tool": "disfigurement-index-frontend-review-agent",
        "mode": "local_deterministic_audit",
        "root": str(root),
        "filesReviewed": sorted(files),
        "pageSignals": page_summaries,
        "scores": scores,
        "findings": [asdict(finding) for finding in findings],
        "pendingForClinicalUse": [
            "completed Disfigurement Index protocol and scoring formula",
            "locked reference test cases and missing-data rules",
            "inter-rater and intra-rater reliability study",
            "external clinical validation and subgroup robustness review",
            "privacy, security, regulatory, and institutional approvals before PHI use",
            "provenance review for any future AI image-analysis model or dataset",
        ],
        "externalModelCalls": False,
    }


def compare_agents() -> dict[str, Any]:
    agents = (
        AgentProfile("Codex", "repo-aware coding agent", ("multi-file edits", "test loop", "local code review"), ("provider-managed", "browser control depends on local connector availability"), "https://openai.com/codex"),
        AgentProfile("Claude Code", "terminal coding agent", ("multi-file edits", "terminal workflow", "large context"), ("provider-managed", "requires separate account and install"), "https://www.anthropic.com/claude-code"),
        AgentProfile("Gemini CLI", "open-source terminal coding harness", ("terminal workflow", "open-source harness", "repo exploration"), ("model/API terms are separate", "visual QA needs setup"), "https://github.com/google-gemini/gemini-cli"),
        AgentProfile("OpenHands SDK", "open-source agent framework", ("self-managed harness", "provider flexibility", "sandbox policy control"), ("higher setup cost", "requires explicit tool policy"), "https://docs.openhands.dev"),
    )
    executable = {"Codex": "codex", "Claude Code": "claude", "Gemini CLI": "gemini", "OpenHands SDK": "openhands"}
    return {
        "method": "capability matrix, not a model benchmark",
        "evaluationRubric": [
            {"criterion": "clinical boundary", "weight": 20, "check": "No diagnostic, treatment, medico-legal, or validation claim is introduced."},
            {"criterion": "accessibility", "weight": 15, "check": "Labels, focus, landmarks, contrast, and mobile navigation remain usable."},
            {"criterion": "calculator correctness", "weight": 20, "check": "Formula version, domains, weights, and score gates remain covered by tests."},
            {"criterion": "privacy", "weight": 15, "check": "No patient images, identifiers, credentials, or PHI are committed or uploaded."},
            {"criterion": "maintainability", "weight": 15, "check": "Small reviewed patches, clear docs, and reproducible commands."},
            {"criterion": "design clarity", "weight": 15, "check": "Minimal clinical interface with obvious primary actions and no marketing overclaim."},
        ],
        "releaseGates": [
            "all tests pass",
            "frontend review agent has no high findings",
            "algorithm contract is valid",
            "documentation preserves research-only language",
            "human reviewer approves any clinical, AI, data, or deployment change",
        ],
        "agents": [{**asdict(agent), "availableOnPath": shutil.which(executable[agent.name]) is not None} for agent in agents],
    }


def improvement_prompt(audit: dict[str, Any], comparison: dict[str, Any]) -> str:
    return f"""You are reviewing the Disfigurement Index website, a local-first clinical research prototype for structured disfigurement documentation.

Constraints:
- Do not claim diagnosis, treatment advice, medico-legal validity, clinical validation, or regulatory clearance.
- Preserve doctor-led interpretation and the current local-first storage boundary.
- Do not add patient images, identifiers, credentials, model weights, remote uploads, or external model calls.
- Keep the interface minimal, accessible, responsive, and suitable for repeated clinical use.
- Treat AI image analysis as a future capability until model, dataset, validation, and governance records exist.
- Return a proposed patch plan first. Do not edit files until a human approves it.

Local audit:
{json.dumps(audit, indent=2, sort_keys=True)}

Agent comparison:
{json.dumps(comparison, indent=2, sort_keys=True)}

Deliver:
1. Three highest-impact frontend changes.
2. One safety or privacy concern that should block release if unresolved.
3. The exact tests and browser checks required before merge.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the Disfigurement Index frontend locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    subparsers.add_parser("prompt")
    args = parser.parse_args()

    if args.command == "audit":
        report = audit_frontend(DEFAULT_ROOT)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"{report['tool']} ({report['mode']})")
            print(f"Findings: {len(report['findings'])}")
            for finding in report["findings"]:
                print(f"- [{finding['severity']}] {finding['title']}: {finding['next_action']}")
        return
    if args.command == "compare":
        comparison = compare_agents()
        if args.json:
            print(json.dumps(comparison, indent=2, sort_keys=True))
        else:
            print(comparison["method"])
            for agent in comparison["agents"]:
                print(f"- {agent['name']}: {'available' if agent['availableOnPath'] else 'not on PATH'}")
        return
    if args.command == "prompt":
        print(improvement_prompt(audit_frontend(DEFAULT_ROOT), compare_agents()))


if __name__ == "__main__":
    main()
