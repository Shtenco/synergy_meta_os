import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.production_artifact_preflight_v1 import (
    ArtifactPreflightError,
    canonical_digest,
    verify_file,
)


class ProductionArtifactPreflightV1Tests(unittest.TestCase):
    def test_canonical_digest_is_stable(self):
        payload = {"b": 2, "a": 1}
        expected = hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
        self.assertEqual(canonical_digest(payload), expected)

    def test_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ArtifactPreflightError):
                verify_file(Path(tmp) / "missing.pyz", "0" * 64, 1, "missing")

    def test_wrong_size_rejected_before_hash_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.bin"
            path.write_bytes(b"x")
            with self.assertRaises(ArtifactPreflightError):
                verify_file(path, hashlib.sha256(b"x").hexdigest(), 2, "artifact")

    def test_wrong_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.bin"
            path.write_bytes(b"x")
            with self.assertRaises(ArtifactPreflightError):
                verify_file(path, "0" * 64, 1, "artifact")


if __name__ == "__main__":
    unittest.main()
