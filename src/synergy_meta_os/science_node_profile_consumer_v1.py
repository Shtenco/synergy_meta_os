from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .capability_registry_consumer_v1 import canonical_json
from .manifest_v2 import verify_manifest_v2


class ScienceProfileConsumerError(ValueError):
    pass


SCIENCE_PROFILE_DIGEST = "0c9b82e591c5aa30d1f9b499edee02c0b56643af825bbb7eecb93f8651659107"
SCIENCE_CAPABILITIES = ("CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY", "SCIENCE_RESEARCH")
SCIENCE_FORBIDDEN_KINDS = ("AUTOPILOT", "BLOCKCHAIN", "FINANCIAL_OS", "METAPAY", "MIDAS")
SCIENCE_SERVICES = {
    "content-cache": ("CONTENT_CACHE", "Shtenco/synergynet", ("CONTENT_CACHE",)),
    "nexus": ("NEXUS", "Shtenco/agi_nexus", ("NEXUS_COMPUTE",)),
    "science-agent": ("SCIENCE_AGENT", "Shtenco/nexus_science_agent", ("SCIENCE_RESEARCH",)),
    "synergynet": ("SYNERGYNET", "Shtenco/synergynet", ("P2P_RELAY",)),
}


@dataclass(frozen=True)
class ScienceProfileConformanceResult:
    profile_id: str
    profile_digest: str
    manifest_body_digest: str
    capability_registry_digest: str
    status: str
    blockers: tuple[str, ...]
    financial_authority: str = "NONE"
    payment_authority: str = "NONE"
    accounting_authority: str = "NONE"
    execution_authority: str = "NONE"


def _profile_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("profile_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def verify_science_profile(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {"schema", "profile_id", "allowed_capabilities", "required_services", "forbidden_service_kinds", "financial_authority", "payment_authority", "accounting_authority", "execution_authority", "status", "profile_digest"}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ScienceProfileConsumerError("unexpected science profile shape")
    if payload["schema"] != "synergy.node-profile/v1" or payload["profile_id"] != "SCIENCE_RESEARCH_NODE":
        raise ScienceProfileConsumerError("unexpected science profile identity")
    if tuple(payload["allowed_capabilities"]) != SCIENCE_CAPABILITIES:
        raise ScienceProfileConsumerError("science capability profile drifted")
    if tuple(payload["forbidden_service_kinds"]) != SCIENCE_FORBIDDEN_KINDS:
        raise ScienceProfileConsumerError("science forbidden-service boundary drifted")
    services = payload["required_services"]
    if not isinstance(services, list) or len(services) != len(SCIENCE_SERVICES):
        raise ScienceProfileConsumerError("science service composition drifted")
    seen: set[str] = set()
    for service in services:
        if not isinstance(service, dict) or set(service) != {"service_id", "kind", "repository", "required_capabilities"}:
            raise ScienceProfileConsumerError("science service shape mismatch")
        sid = service["service_id"]
        if sid in seen or sid not in SCIENCE_SERVICES:
            raise ScienceProfileConsumerError("unexpected or duplicate science service")
        seen.add(sid)
        kind, repository, required = SCIENCE_SERVICES[sid]
        if service["kind"] != kind or service["repository"] != repository or tuple(service["required_capabilities"]) != required:
            raise ScienceProfileConsumerError("science service identity/capability drifted")
    if seen != set(SCIENCE_SERVICES):
        raise ScienceProfileConsumerError("science service set incomplete")
    for field in ("financial_authority", "payment_authority", "accounting_authority", "execution_authority"):
        if payload[field] != "NONE":
            raise ScienceProfileConsumerError(f"science profile cannot grant {field}")
    if payload["status"] != "ARCHITECTURE_PROFILE_ONLY":
        raise ScienceProfileConsumerError("unexpected science profile status")
    digest = _profile_digest(payload)
    if digest != payload["profile_digest"] or digest != SCIENCE_PROFILE_DIGEST:
        raise ScienceProfileConsumerError("science profile digest mismatch")
    return payload


def evaluate_signed_manifest_v2_for_science_profile(*, profile: dict[str, Any], signed_manifest: dict[str, Any], capability_registry: dict[str, Any], key_resolver: Callable[[str], Ed25519PublicKey], now=None) -> ScienceProfileConformanceResult:
    verify_science_profile(profile)
    body = verify_manifest_v2(signed_manifest, capability_registry, key_resolver, now=now)
    blockers: list[str] = []
    capabilities = tuple(body["capabilities"])
    if capabilities != SCIENCE_CAPABILITIES:
        blockers.append("CAPABILITY_SET_MISMATCH")
    forbidden_caps = {"AUTOPILOT_SERVICE", "BLOCKCHAIN_VALIDATOR", "FINANCIAL_SERVICE", "METAPAY_GATEWAY", "MIDAS_ANALYSIS"}
    if any(cap in forbidden_caps for cap in capabilities):
        blockers.append("FORBIDDEN_CAPABILITY_PRESENT")

    services = body["services"]
    service_by_id = {service["service_id"]: service for service in services}
    if len(service_by_id) != len(services):
        blockers.append("DUPLICATE_SERVICE_ID")
    if set(service_by_id) != set(SCIENCE_SERVICES):
        blockers.append("SERVICE_SET_MISMATCH")
    for sid, (kind, repository, required) in SCIENCE_SERVICES.items():
        service = service_by_id.get(sid)
        if service is None:
            blockers.append(f"MISSING_SERVICE:{sid}")
            continue
        if service["kind"] != kind:
            blockers.append(f"SERVICE_KIND_MISMATCH:{sid}")
        if service["repository"] != repository:
            blockers.append(f"SERVICE_REPOSITORY_MISMATCH:{sid}")
        if tuple(service["required_capabilities"]) != required:
            blockers.append(f"SERVICE_CAPABILITY_MISMATCH:{sid}")
        if service["desired_state"] != "ENABLED":
            blockers.append(f"SERVICE_NOT_ENABLED:{sid}")
    if any(service["kind"] in set(SCIENCE_FORBIDDEN_KINDS) for service in services):
        blockers.append("FORBIDDEN_SERVICE_KIND_PRESENT")

    blockers = sorted(set(blockers))
    return ScienceProfileConformanceResult(
        profile_id=profile["profile_id"],
        profile_digest=profile["profile_digest"],
        manifest_body_digest=signed_manifest["body_digest"],
        capability_registry_digest=body["capability_registry_digest"],
        status="PROFILE_CONFORMANT" if not blockers else "SIGNED_BUT_PROFILE_NONCONFORMANT",
        blockers=tuple(blockers),
    )
