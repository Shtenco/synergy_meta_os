from __future__ import annotations

import hashlib
import json
from typing import Any


class CapabilityRegistryError(ValueError):
    pass


RISK_TIERS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EXPECTED_AUTHORITY = {
    "architecture_authority": "Shtenco/synergy_system",
    "runtime_manifest_authority": "Shtenco/synergy_meta_os",
    "capability_does_not_grant_domain_authority": True,
    "execution_authority": "NONE",
}


def canonical_json(value: Any) -> bytes:
    def check(v: Any) -> None:
        if v is None or isinstance(v, (str, bool)):
            return
        if isinstance(v, int) and not isinstance(v, bool):
            if abs(v) > 2**53 - 1:
                raise CapabilityRegistryError("unsafe integer")
            return
        if isinstance(v, float):
            raise CapabilityRegistryError("floats are forbidden")
        if isinstance(v, list):
            for item in v:
                check(item)
            return
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise CapabilityRegistryError("keys must be strings")
            for item in v.values():
                check(item)
            return
        raise CapabilityRegistryError(f"unsupported value: {type(v)!r}")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_capability_registry_v1(payload: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    expected = {"schema", "registry_id", "generation", "capabilities", "service_kinds", "authority_semantics"}
    if set(payload) != expected:
        raise CapabilityRegistryError("unexpected registry shape")
    if payload["schema"] != "synergy.capability-registry/v1" or payload["registry_id"] != "synergy-core-capabilities" or payload["generation"] != 1:
        raise CapabilityRegistryError("unexpected registry identity")
    if payload["authority_semantics"] != EXPECTED_AUTHORITY:
        raise CapabilityRegistryError("authority semantics mismatch")

    cap_map: dict[str, dict[str, Any]] = {}
    cap_ids: list[str] = []
    for cap in payload["capabilities"]:
        if not isinstance(cap, dict) or set(cap) != {"capability_id", "authority_grant", "risk_tier"}:
            raise CapabilityRegistryError("unexpected capability shape")
        cid = cap["capability_id"]
        if not isinstance(cid, str) or not cid or cid != cid.upper():
            raise CapabilityRegistryError("invalid capability id")
        if cap["authority_grant"] != "NONE" or cap["risk_tier"] not in RISK_TIERS:
            raise CapabilityRegistryError("invalid capability semantics")
        cap_ids.append(cid)
        cap_map[cid] = cap
    if cap_ids != sorted(set(cap_ids)):
        raise CapabilityRegistryError("capabilities must be sorted and unique")

    kind_map: dict[str, dict[str, Any]] = {}
    kind_ids: list[str] = []
    for item in payload["service_kinds"]:
        if not isinstance(item, dict) or set(item) != {"kind", "repository", "required_capabilities"}:
            raise CapabilityRegistryError("unexpected service kind shape")
        kind = item["kind"]
        repo = item["repository"]
        required = item["required_capabilities"]
        if not isinstance(kind, str) or not kind or kind != kind.upper():
            raise CapabilityRegistryError("invalid service kind")
        if not isinstance(repo, str) or not repo.startswith("Shtenco/"):
            raise CapabilityRegistryError("invalid service repository")
        if not isinstance(required, list) or not required or required != sorted(set(required)):
            raise CapabilityRegistryError("required capabilities must be sorted and unique")
        if any(cap not in cap_map for cap in required):
            raise CapabilityRegistryError("service kind references unknown capability")
        kind_ids.append(kind)
        kind_map[kind] = item
    if kind_ids != sorted(set(kind_ids)):
        raise CapabilityRegistryError("service kinds must be sorted and unique")

    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    return digest, cap_map, kind_map
