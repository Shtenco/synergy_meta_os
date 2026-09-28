from __future__ import annotations
from typing import Any

STORE_SOURCE_CONTRACT_ID="synergy.app.store-source-evidence/v1"
SUPERAPP_SURFACE_CONTRACT_ID="synergy.app.superapp-surface/v1"

def _digest(payload:dict[str,Any],field:str)->str:
    value=str(payload.get(field,"")).lower()
    if len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid {field}")
    return value

def consume_store_source_evidence(payload:dict[str,Any])->dict[str,Any]:
    if payload.get("source_verified") is not True:
        raise ValueError("mobile source verification required")
    if bool(payload.get("artifact_built")) or bool(payload.get("store_published")):
        raise ValueError("source evidence cannot self-promote build/publication claims")
    if bool(payload.get("deployment_authority")):
        raise ValueError("source evidence cannot grant deployment authority")
    for f in ("android_gradle_sha256","android_manifest_sha256","ios_project_sha256","ios_privacy_sha256"):
        _digest(payload,f)
    return {
        "kind":"STORE_SOURCE_EVIDENCE",
        "app_id":str(payload["app_id"]),
        "version":str(payload["version"]),
        "source_verified":True,
        "artifact_built":False,
        "store_published":False,
        "deployment_authority":False,
    }

def consume_superapp_surface(payload:dict[str,Any])->dict[str,Any]:
    if payload.get("source_surface_verified") is not True:
        raise ValueError("super-app source surface verification required")
    if bool(payload.get("android_artifact_built")) or bool(payload.get("deployment_authority")):
        raise ValueError("source surface cannot self-promote build/deployment")
    for f in ("manifest_sha256","index_sha256","android_gradle_sha256","android_wrapper_sha256"):
        _digest(payload,f)
    return {
        "kind":"SUPERAPP_SOURCE_SURFACE",
        "name":str(payload["name"]),
        "start_url":str(payload["start_url"]),
        "source_surface_verified":True,
        "android_artifact_built":False,
        "deployment_authority":False,
    }
