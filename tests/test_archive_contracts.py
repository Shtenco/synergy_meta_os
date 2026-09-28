from hashlib import sha256

import pytest

from runtime.archive_contracts import verify_archive_evidence


def test_meta_os_accepts_verified_archive_evidence(tmp_path):
    p=tmp_path/"artifact.bin"
    p.write_bytes(b"archive")
    payload={
        "round_trip_verified":True,
        "archive_sha256":sha256(b"archive").hexdigest(),
        "archive_bytes":7,
    }
    verify_archive_evidence(payload,p)


def test_meta_os_rejects_archive_hash_mismatch(tmp_path):
    p=tmp_path/"artifact.bin"
    p.write_bytes(b"archive")
    with pytest.raises(ValueError):
        verify_archive_evidence({
            "round_trip_verified":True,
            "archive_sha256":"1"*64,
            "archive_bytes":7,
        },p)
