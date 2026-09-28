from __future__ import annotations

from pathlib import Path
from typing import Any

from .orchestrator import load_manifest, verify_manifest


CONTRACT_ID = "synergy.runtime.node-manifest/v1"
AUTHORITY = "runtime_orchestration"


def node_manifest_payload(manifest_path: Path, root: Path | None = None) -> dict[str, Any]:
    obj = verify_manifest(manifest_path, root) if root is not None else load_manifest(manifest_path)
    return {
        "node_id": obj["node_id"],
        "profile": obj["profile"],
        "attested": bool(obj["attested"]),
        "development": bool(obj["development"]),
        "generation": int(obj.get("generation", 1)),
        "services": [
            {
                "name": s["name"],
                "role": s["role"],
                "artifact": s["artifact"],
                "sha256": s["sha256"].lower(),
                "argv": list(s["argv"]),
                "capabilities": list(s["capabilities"]),
                "limits": dict(s["limits"]),
            }
            for s in obj["services"]
        ],
    }
