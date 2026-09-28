from __future__ import annotations

from pathlib import Path
from typing import Any

from .orchestrator import sha256_file


UPSTREAM_CONTRACT_ID = "synergy.archive.evidence/v1"


def verify_archive_evidence(payload: dict[str, Any], archive_path: Path) -> None:
    if payload.get("round_trip_verified") is not True:
        raise ValueError("archive evidence is not lossless-round-trip verified")
    expected=str(payload.get("archive_sha256","")).lower()
    if len(expected)!=64:
        raise ValueError("invalid archive_sha256")
    actual=sha256_file(archive_path)
    if actual != expected:
        raise ValueError("archive hash mismatch")
    size=int(payload.get("archive_bytes",-1))
    if archive_path.stat().st_size != size:
        raise ValueError("archive byte-size mismatch")
