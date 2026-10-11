"""Synthetic HTTP traversal checks; no database or clinical server initialization."""
import unittest
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch

import server as app


class StaticPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.root = self.folder / "site"
        self.root.mkdir()
        (self.root / "index.html").write_text("SYNTHETIC_VALID_INDEX")
        (self.root / "page.html").write_text("SYNTHETIC_VALID_PAGE")
        self.outside = self.folder / "outside.txt"
        self.outside.write_text("SYNTHETIC_OUTSIDE_ROOT")
        root_patch = patch.object(app, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        db_patch = patch.object(app, "init_db", side_effect=AssertionError("No database allowed"))
        self.init_db = db_patch.start()
        self.addCleanup(db_patch.stop)

        class QuietHandler(app.AppHandler):
            def log_message(self, *args):
                pass

        self.http = app.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.worker = Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join(timeout=2)
        self.assertFalse(self.worker.is_alive())
        self.init_db.assert_not_called()
        self.assertFalse((self.root / "data").exists())

    def request(self, path):
        connection = HTTPConnection("127.0.0.1", self.http.server_port, timeout=3)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.read().decode()
        finally:
            connection.close()

    def assert_denied(self, path):
        status, body = self.request(path)
        self.assertEqual(status, HTTPStatus.FORBIDDEN)
        self.assertNotIn("SYNTHETIC_OUTSIDE_ROOT", body)

    def test_valid_pages_are_served_from_configured_root(self):
        self.assertEqual(self.request("/"), (HTTPStatus.OK, "SYNTHETIC_VALID_INDEX"))
        self.assertEqual(self.request("/page.html"), (HTTPStatus.OK, "SYNTHETIC_VALID_PAGE"))
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "index.html").write_text("SYNTHETIC_VALID_NESTED_INDEX")
        self.assertEqual(self.request("/nested/"), (HTTPStatus.OK, "SYNTHETIC_VALID_NESTED_INDEX"))
        self.assertEqual(
            self.request("/nested/index.html"), (HTTPStatus.OK, "SYNTHETIC_VALID_NESTED_INDEX")
        )

    def test_encoded_parent_traversal_is_denied(self):
        for path in ["/%2e%2e/outside.txt", "/..%2foutside.txt", "/%2e%2e%2foutside.txt"]:
            with self.subTest(path=path):
                self.assert_denied(path)

    def test_outside_file_and_directory_symlinks_are_denied(self):
        (self.root / "escape.txt").symlink_to(self.outside)
        (self.root / "escape-dir").symlink_to(self.folder, target_is_directory=True)
        for path in ["/escape.txt", "/escape-dir/outside.txt"]:
            with self.subTest(path=path):
                self.assert_denied(path)

    def test_root_and_nested_index_symlinks_cannot_escape(self):
        (self.root / "index.html").unlink()
        (self.root / "index.html").symlink_to(self.outside)
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "index.html").symlink_to(self.outside)
        for path in ["/", "/nested/"]:
            with self.subTest(path=path):
                self.assert_denied(path)
