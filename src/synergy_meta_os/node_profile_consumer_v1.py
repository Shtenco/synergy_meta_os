from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .manifest import ManifestError, canonical_json, verify_manifest


class NodeProfileConsumerError(ValueError):
    pass


RESEARCH_PROFILE_DIGEST = "406740705e853fa51ad4eacf7a01925fbe4b5cec491be35ea12ba777d217d714"
_RESEARCH_CAPABILITIES = ("CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY")
_RESEARCH_FORBIDDEN_KINDS = ("AUTOPILOT", "BLOCKCHAIN", "FINANCIAL_OS", "METAPAY")
_RESEARCH_SERVICES = {
    "content-cache": ("CONTENT_CACHE", "Shtenco/synergynet", ("CONTENT_CACHE",)),
    "nexus": ("NEXUS", "Shtenco/agi_nexus", ("NEXUS_COMPUTE",)),
    "synergynet": ("SYNERGYNET", "Shtenco/synergynet", ("P2P_RELAY",)),
}


@dataclass(frozen=True)
class ProfileConformanceResult:
    profile_id: str
    profile_digest: str
    manifest_body_digest: str
    status: str
    blockers: tuple[str, ...]
    financial_authority: str = "NONE"
    payment_authority: str = "NONE"
    accounting_authority: str = "NONE"
    execution_authority: str = "NONE"


def profile_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("profile_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def verify_research_profile(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema",
        "profile_id",
        "allowed_capabilities",
        "required_services",
        "forbidden_service_kinds",
        "financial_authority",
        "payment_authority",
        "accounting_authority",
        "execution_authority",
        "status",
        "profile_digest",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise NodeProfileConsumerError("unexpected node-profile shape")
    if payload["schema"] != "synergy.node-profile/v1" or payload["profile_id"] != "RESEARCH_COMPUTE_NODE":
        raise NodeProfileConsumerError("unexpected research node profile schema/id")
    if payload["allowed_capabilities"] != list(_RESEARCH_CAPABILITIES):
        raise NodeProfileConsumerError("research capability profile drifted")
    if payload["forbidden_service_kinds"] != list(_RESEARCH_FORBIDDEN_KINDS):
        raise NodeProfileConsumerError("research forbidden-service boundary drifted")
    services = payload["required_services"]
    if not isinstance(services, list) or len(services) != len(_RESEARCH_SERVICES):
        raise NodeProfileConsumerError("research service composition drifted")
    seen: set[str] = set()
    for service in services:
        if not isinstance(service, dict) or set(service) != {
            "service_id", "kind", "repository", "required_capabilities"
        }:
            raise NodeProfileConsumerError("research service shape mismatch")
        sid = service["service_id"]
        if sid in seen or sid not in _RESEARCH_SERVICES:
            raise NodeProfileConsumerError("unexpected or duplicate research service")
        seen.add(sid)
        kind, repository, required = _RESEARCH_SERVICES[sid]
        if service["kind"] != kind or service["repository"] != repository:
            raise NodeProfileConsumerError("research service identity drifted")
        if tuple(service["required_capabilities"]) != required:
            raise NodeProfileConsumerError("research service capability drifted")
    if seen != set(_RESEARCH_SERVICES):
        raise NodeProfileConsumerError("research service set incomplete")
    for field in (
        "financial_authority", "payment_authority", "accounting_authority", "execution_authority"
    ):
        if payload[field] != "NONE":
            raise NodeProfileConsumerError(f"research profile cannot grant {field}")
    if payload["status"] != "ARCHITECTURE_PROFILE_ONLY":
        raise NodeProfileConsumerError("unexpected node-profile status")
    digest = profile_digest(payload)
    if payload["profile_digest"] != digest or digest != RESEARCH_PROFILE_DIGEST:
        raise NodeProfileConsumerError("research profile digest mismatch")
    return payload


def evaluate_signed_manifest_for_research_profile(
    *,
    profile: dict[str, Any],
    signed_manifest: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    now=None,
) -> ProfileConformanceResult:
    """Verify node identity first, then independently enforce architecture composition.

    A valid signature proves who signed the manifest. It does not prove that the
    manifest is allowed for RESEARCH_COMPUTE_NODE.
    """

    verify_research_profile(profile)
    body = verify_manifest(signed_manifest, key_resolver, now=now)
    blockers: list[str] = []

    capabilities = tuple(body["capabilities"])
    if capabilities != _RESEARCH_CAPABILITIES:
        blockers.append("CAPABILITY_SET_MISMATCH")
    if any(cap in {"BLOCKCHAIN_VALIDATOR", "METAPAY_GATEWAY", "FINANCIAL_SERVICE", "AUTOPILOT_SERVICE"} for cap in capabilities):
        blockers.append("FORBIDDEN_CAPABILITY_PRESENT")

    services = body["services"]
    service_by_id = {service["service_id"]: service for service in services}
    if len(service_by_id) != len(services):
        blockers.append("DUPLICATE_SERVICE_ID")
    if set(service_by_id) != set(_RESEARCH_SERVICES):
        blockers.append("SERVICE_SET_MISMATCH")

    for sid, (kind, repository, required_caps) in _RESEARCH_SERVICES.items():
        service = service_by_id.get(sid)
        if service is None:
            blockers.append(f"MISSING_SERVICE:{sid}")
            continue
        if service["kind"] != kind:
            blockers.append(f"SERVICE_KIND_MISMATCH:{sid}")
        if service["repository"] != repository:
            blockers.append(f"SERVICE_REPOSITORY_MISMATCH:{sid}")
        if tuple(service["required_capabilities"]) != required_caps:
            blockers.append(f"SERVICE_CAPABILITY_MISMATCH:{sid}")
        if service["desired_state"] != "ENABLED":
            blockers.append(f"SERVICE_NOT_ENABLED:{sid}")

    forbidden_kinds = set(_RESEARCH_FORBIDDEN_KINDS)
    if any(service["kind"] in forbidden_kinds for service in services):
        blockers.append("FORBIDDEN_SERVICE_KIND_PRESENT")

    blockers = sorted(set(blockers))
    status = "PROFILE_CONFORMANT" if not blockers else "SIGNED_BUT_PROFILE_NONCONFORMANT"
    return ProfileConformanceResult(
        profile_id=profile["profile_id"],
        profile_digest=profile["profile_digest"],
        manifest_body_digest=signed_manifest["body_digest"],
        status=status,
        blockers=tuple(blockers),
    )


def require_profile_conformance(result: ProfileConformanceResult) -> None:
    if result.status != "PROFILE_CONFORMANT" or result.blockers:
        raise ManifestError("signed manifest does not conform to selected architecture profile")
