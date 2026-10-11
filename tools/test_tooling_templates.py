import hashlib
import json
import tarfile
import unittest
from io import BytesIO

from coderabbit_review import review_result
from install_ci_tools import executable


class Templates(unittest.TestCase):
    def test_review_completion_and_incomplete_results(self):
        complete = {"type": "complete", "status": "review_completed"}
        for code, extra in [(1, {}), (0, {"outcome": "failed"}), (0, {"unreviewedFileCount": 1})]:
            result, status = review_result(json.dumps(complete | extra), code)
            self.assertEqual((result["status"], status), ("incomplete", 1))
        result, status = review_result(json.dumps(complete | {"reused": True}), 0)
        self.assertEqual((result["status"], status, result["reused"]), ("completed", 0, True))

    def test_successful_skip_is_not_review_approval(self):
        result, status = review_result(json.dumps({"type": "complete", "status": "review_skipped"}), 0)
        self.assertEqual((result["status"], status), ("skipped", 1))
        self.assertEqual(review_result('', 0)[1], 1)

    def test_findings_are_separate_from_completion(self):
        stream = '\n'.join(map(json.dumps, [{"type": "finding", "severity": "major"}, {"type": "complete", "status": "review_completed"}]))
        result, status = review_result(stream, 0)
        self.assertEqual(result["severities"], {"major": 1})
        self.assertEqual(result["findings"], 1)
        self.assertEqual(status, 0)  # Advisory completion, never a findings approval gate.

    def test_archive_checksum_and_symlink_rejection(self):
        for regular in [True, False]:
            output = BytesIO()
            with tarfile.open(fileobj=output, mode='w:gz') as archive:
                member = tarfile.TarInfo('../tool')
                if regular:
                    member.size = 2
                    archive.addfile(member, BytesIO(b'ok'))
                else:
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/outside'
                    archive.addfile(member)
            data = output.getvalue()
            with self.assertRaises(ValueError):
                executable(data, '0' * 64, 'tool')
            digest = hashlib.sha256(data).hexdigest()
            if regular:
                self.assertEqual(executable(data, digest, 'tool'), b'ok')
            else:
                with self.assertRaises(ValueError):
                    executable(data, digest, 'tool')


if __name__ == '__main__':
    unittest.main()
