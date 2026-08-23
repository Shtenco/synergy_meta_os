from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

EXPECTED_RELEASE_SHA256 = "afba4eb7508564292f6695dbef69e9a043a998da8a2e4b587922c17bbefb37cb"
EXPECTED_RELEASE_SIZE = 1045560
EXPECTED_NEXUS_SHA256 = "e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325"
EXPECTED_NEXUS_SIZE = 56965
EXPECTED_SYNERGYNET_SHA256 = "7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7"
EXPECTED_SYNERGYNET_SIZE = 12837
NEXUS_MEMBER = "artifacts/nexus/nexus_e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325.pyz"


class ArtifactPreflightError(ValueError):
    pass


def sha256_stream(handle: BinaryIO) -> str:
    h = hashlib.sha256()
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            return h.hexdigest()
        h.update(chunk)


def sha256_path(path: Path) -> str:
    with path.open("rb") as handle:
        return sha256_stream(handle)


def canonical_digest(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_file(path: Path, expected_sha256: str, expected_size: int, label: str) -> dict:
    if not path.is_file():
        raise ArtifactPreflightError(f"{label} missing: {path}")
    size = path.stat().st_size
    if size != expected_size:
        raise ArtifactPreflightError(f"{label} size mismatch: {size} != {expected_size}")
    digest = sha256_path(path)
    if digest != expected_sha256:
        raise ArtifactPreflightError(f"{label} sha256 mismatch: {digest}")
    return {"sha256": digest, "size": size}


def run_preflight(release_zip: Path, synergynet_pyz: Path) -> dict:
    release = verify_file(release_zip, EXPECTED_RELEASE_SHA256, EXPECTED_RELEASE_SIZE, "AUTOPILOT release ZIP")
    synergynet = verify_file(synergynet_pyz, EXPECTED_SYNERGYNET_SHA256, EXPECTED_SYNERGYNET_SIZE, "SynergyNet artifact")

    with zipfile.ZipFile(release_zip, "r") as archive:
        try:
            info = archive.getinfo(NEXUS_MEMBER)
        except KeyError as exc:
            raise ArtifactPreflightError("exact NEXUS member missing from release ZIP") from exc
        if info.file_size != EXPECTED_NEXUS_SIZE:
            raise ArtifactPreflightError("NEXUS member size mismatch")
        with archive.open(info, "r") as handle:
            nexus_sha = sha256_stream(handle)
        if nexus_sha != EXPECTED_NEXUS_SHA256:
            raise ArtifactPreflightError("NEXUS member sha256 mismatch")

    payload = {
        "schema": "synergy.meta-os-production-artifact-verification/v1",
        "node_id": "synergy-autopilot-v5-ai-node",
        "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "release_archive": release,
        "nexus_artifact": {"sha256": nexus_sha, "size": EXPECTED_NEXUS_SIZE, "member": NEXUS_MEMBER},
        "synergynet_artifact": synergynet,
        "preproduction_release_digest": "717b473fc67fbbdef89385d04b260ae2c8a8e85c75365ba8627785e1c8c271c7",
        "deployment_reference_digest": "19375c02a286a4c14e704ad0496d1c6084ddb00e7c4bcf3506a304a6b0946b70",
        "production_bootstrap_contract_digest": "605c6c953e998efb9585a88c1c8f1a022d7160e3448139c2b80a33e6b6cbabd3",
        "status": "PASS_EXACT_ARTIFACTS_VERIFIED_NOT_STARTED",
        "startup_performed": False,
        "execution_authority": "NONE",
    }
    payload["artifact_verification_digest"] = canonical_digest(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify exact AUTOPILOT/NEXUS/SynergyNet artifacts before any production start.")
    parser.add_argument("--release-zip", type=Path, required=True)
    parser.add_argument("--synergynet-pyz", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = run_preflight(args.release_zip, args.synergynet_pyz)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
