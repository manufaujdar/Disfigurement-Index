"""Negative regressions for the repository-owned outgoing-commit check."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "engineering_checks", Path(__file__).resolve().parents[1] / "scripts/engineering_checks.py"
)
assert SPEC is not None and SPEC.loader is not None
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)

class EngineeringChecksTests(unittest.TestCase):
    def test_missing_relative_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "present.md").write_text("# Present\n")
            doc = root / "README.md"
            doc.write_text("[present](present.md#heading)\n[missing](missing.md)\n")
            with patch.object(checks, "ROOT", root):
                self.assertEqual(checks.document_errors(doc), ["README.md: missing relative link missing.md"])

    def test_examples_and_external_workspace_links_are_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            doc = root / "README.md"
            doc.write_text("```md\n[example](not-real.md)\n```\n[workspace](../private.md)\n[remote](https://example.com/)\n")
            with patch.object(checks, "ROOT", root):
                self.assertEqual(checks.document_errors(doc), [])

    def test_dirty_tree_cannot_certify_outgoing_commit(self):
        with patch.object(checks, "resolve", return_value="a" * 40), patch.object(checks, "git", return_value=" M README.md"):
            with self.assertRaisesRegex(ValueError, "working tree must be clean"):
                checks.run("a" * 40)

    def test_resolved_ref_must_be_immutable_sha(self):
        with patch.object(checks, "git", return_value="invalid-ref; command"):
            with self.assertRaisesRegex(ValueError, "immutable commit SHA"):
                checks.resolve("main")
