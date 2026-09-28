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


def consume_archive_benchmark_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("round_trip_verified") is not True:
        raise ValueError("benchmark must prove exact round-trip")
    if payload.get("temporal_cutoff_valid") is not True:
        raise ValueError("benchmark temporal cutoff invalid")
    if bool(payload.get("deployment_authority")):
        raise ValueError("benchmark cannot grant deployment authority")
    digest = str(payload.get("target_sha256", "")).lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid target sha256")
    return {
        "kind": "ARCHIVE_BENCHMARK",
        "benchmark_id": str(payload["benchmark_id"]),
        "target_sha256": digest,
        "original_bytes": int(payload["original_bytes"]),
        "container_bytes": int(payload["container_bytes"]),
        "round_trip_verified": True,
        "deployment_authority": False,
    }
