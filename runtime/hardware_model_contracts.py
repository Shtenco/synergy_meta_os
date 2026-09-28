from __future__ import annotations
from typing import Any

UPSTREAM_CONTRACT_ID = "synergy.runtime.hardware-model/v1"

def consume_hardware_model(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("model_status","")) != "MODEL_NOT_SILICON":
        raise ValueError("hardware evidence must remain an analytical model")
    if bool(payload.get("measured_silicon")):
        raise ValueError("modeled XPU cannot self-promote to measured silicon")
    if bool(payload.get("deployment_authority")):
        raise ValueError("hardware model cannot grant deployment authority")
    digest=str(payload.get("config_sha256","")).lower()
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid config digest")
    return {
        "kind":"HARDWARE_MODEL",
        "model_id":str(payload["model_id"]),
        "config_sha256":digest,
        "eml_primitives_per_s":float(payload["eml_primitives_per_s"]),
        "hbm_bytes_per_s":float(payload["hbm_bytes_per_s"]),
        "measured_silicon":False,
        "deployment_authority":False,
    }
