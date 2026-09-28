from __future__ import annotations

from typing import Any


UPSTREAM_CONTRACT_ID = "synergy.engineering.change-evidence/v1"


def require_deployable_change(payload: dict[str, Any], *, expected_repository: str | None = None) -> None:
    review = str(payload.get("review_status", "")).upper()
    if review != "APPROVED":
        raise ValueError(f"change is not approved: {review}")
    if expected_repository is not None and payload.get("repository") != expected_repository:
        raise ValueError("change evidence repository mismatch")
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("change evidence has no checks")
    failed = [c for c in checks if str(c.get("status", "")).upper() != "PASS"]
    if failed:
        raise ValueError("all engineering checks must PASS before deployment")
    if not payload.get("requirements"):
        raise ValueError("change evidence has no requirement provenance")
    artifact = payload.get("artifact_sha256")
    if artifact is not None:
        artifact = str(artifact).lower()
        if len(artifact) != 64 or any(c not in "0123456789abcdef" for c in artifact):
            raise ValueError("invalid artifact_sha256")
