"""Native Git push range contracts without executing product commands."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "native_pre_push", Path(__file__).resolve().parents[1] / "scripts/native_pre_push.py"
)
assert SPEC is not None and SPEC.loader is not None
hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hook)

class NativePushTests(unittest.TestCase):
    def test_exact_remote_sha_is_propagated(self):
        head, base = "a" * 40, "b" * 40
        self.assertEqual(hook.outgoing_base([f"HEAD {head} refs/heads/main {base}"], head), base)

    def test_different_outgoing_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "checked-out HEAD"):
            hook.outgoing_base([f"HEAD {'a' * 40} refs/heads/main {'b' * 40}"], "c" * 40)

    def test_non_main_or_injected_sha_is_rejected(self):
        for line in [f"HEAD {'a' * 40} refs/heads/topic {'b' * 40}", f"HEAD {'a' * 40} refs/heads/main invalid;cmd"]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                hook.outgoing_base([line], "a" * 40)

    def test_initial_main_base_is_explicit_and_multiple_refs_rejected(self):
        line = f"HEAD {'a' * 40} refs/heads/main {'0' * 40}"
        self.assertEqual(hook.outgoing_base([line], "a" * 40), "0" * 40)
        with self.assertRaises(ValueError):
            hook.outgoing_base([line, line], "a" * 40)
