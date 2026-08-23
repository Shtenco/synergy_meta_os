from __future__ import annotations

import hashlib
import json
from typing import Any

PROFILE_DIGEST = "3ef4196fff4407ece15470c29f80dcc997e7b0a9e87c9146728187d57493ae63"
ADMISSION_DIGEST = "5ab38263faccd06914ac1ab2edec37ef8cc2efbb5f8f508dccac15a26fb95fcf"
SOURCE_COMMIT = "c39f6f0ee0e37c08366a63ec160c580b9ae954ba"
INTEGRATION_ROOT = "a793250aaa2299fdaf1661e985423c2b62687a19395ceabcc7bb63c005defe54"
LOCATION_EVIDENCE = "4b07c66aa9b682c6a540c357e861b7fe26104efe644195c535d24e6549d34306"
NEXUS_SHA256 = "e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325"
EXPECTED_BLOCKERS = [
    "SYNERGYNET_TRANSPORT_NOT_BOUND",
    "HOST_PROFILE_NOT_BOUND",
    "SUPERVISOR_CONFIG_NOT_MATERIALIZED",
    "DEPLOYMENT_EVIDENCE_NOT_EXECUTED",
]

class AdmissionError(ValueError):
    pass


def canonical_digest(value: dict[str, Any], self_field: str) -> str:
    body = dict(value)
    body.pop(self_field, None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _none_authorities(value: dict[str, Any]) -> None:
    for field in (
        "financial_authority",
        "payment_authority",
        "accounting_authority",
        "host_execution_authority",
        "blockchain_submission_authority",
        "execution_authority",
    ):
        if value.get(field) != "NONE":
            raise AdmissionError(f"authority escalation: {field}")


def verify_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("schema") != "synergy.meta-os-ai-node-profile/v1":
        raise AdmissionError("wrong profile schema")
    if canonical_digest(profile, "profile_digest") != profile.get("profile_digest"):
        raise AdmissionError("profile self digest mismatch")
    if profile.get("profile_digest") != PROFILE_DIGEST:
        raise AdmissionError("unexpected profile generation")
    if profile.get("source_commit") != SOURCE_COMMIT:
        raise AdmissionError("source commit substitution")
    if profile.get("integration_manifest_digest") != INTEGRATION_ROOT:
        raise AdmissionError("integration root substitution")
    if profile.get("release_location_evidence_digest") != LOCATION_EVIDENCE:
        raise AdmissionError("release locator substitution")
    if profile.get("nexus_artifact_sha256") != NEXUS_SHA256:
        raise AdmissionError("NEXUS artifact substitution")
    if profile.get("network_transport_status") != "PENDING_SYNERGYNET_BINDING":
        raise AdmissionError("transport promoted without binding evidence")
    if profile.get("host_profile_status") != "UNBOUND":
        raise AdmissionError("host profile invented")
    if profile.get("supervisor_status") != "NOT_MATERIALIZED":
        raise AdmissionError("supervisor invented")
    if profile.get("running") is not False or profile.get("auto_start") is not False:
        raise AdmissionError("runtime promoted")
    _none_authorities(profile)
    return profile


def verify_admission(profile: dict[str, Any], admission: dict[str, Any]) -> dict[str, Any]:
    verify_profile(profile)
    if admission.get("schema") != "synergy.meta-os-ai-node-admission/v1":
        raise AdmissionError("wrong admission schema")
    if canonical_digest(admission, "admission_digest") != admission.get("admission_digest"):
        raise AdmissionError("admission self digest mismatch")
    if admission.get("admission_digest") != ADMISSION_DIGEST:
        raise AdmissionError("unexpected admission generation")
    if admission.get("profile_digest") != profile["profile_digest"]:
        raise AdmissionError("profile binding mismatch")
    if admission.get("source_commit") != SOURCE_COMMIT:
        raise AdmissionError("source binding mismatch")
    if admission.get("integration_manifest_digest") != INTEGRATION_ROOT:
        raise AdmissionError("integration binding mismatch")
    if admission.get("release_location_evidence_digest") != LOCATION_EVIDENCE:
        raise AdmissionError("location binding mismatch")
    if admission.get("decision") != "ADMITTED_ARTIFACT_RESOLVABLE_NOT_LAUNCHABLE_NOT_RUNNING":
        raise AdmissionError("decision escalation")
    if admission.get("admission_effect") != "REGISTRY_ELIGIBILITY_ONLY":
        raise AdmissionError("admission effect escalation")
    if admission.get("blockers") != EXPECTED_BLOCKERS:
        raise AdmissionError("blocker set drift")
    if admission.get("running") is not False or admission.get("auto_start") is not False:
        raise AdmissionError("runtime promoted")
    _none_authorities(admission)
    return admission
