from __future__ import annotations
from pathlib import Path
from typing import Any
from .orchestrator import sha256_file

UPSTREAM_CONTRACT_ID="synergy.transport.evidence/v1"

def require_transport_delivery(payload:dict[str,Any], *, expected_file:Path|None=None) -> None:
    if payload.get("authenticated") is not True:
        raise ValueError("unauthenticated transport evidence")
    digest=str(payload.get("content_sha256","")).lower()
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid content_sha256")
    route=payload.get("route")
    if not isinstance(route,list) or len(route)<2:
        raise ValueError("transport route missing")
    if expected_file is not None and sha256_file(expected_file)!=digest:
        raise ValueError("transport content hash does not match received artifact")
