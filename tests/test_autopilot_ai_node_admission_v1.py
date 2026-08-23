from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from synergy_meta_os.autopilot_ai_node_admission_v1 import AdmissionError, verify_admission

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles" / "synergy_autopilot_v5_ai_node_profile_v1.json"
ADMISSION = ROOT / "admissions" / "synergy_autopilot_v5_ai_node_admission_v1.json"


def load(path: Path):
    return json.loads(path.read_text())


def fresh_hash(obj: dict, self_field: str):
    import hashlib
    body = dict(obj)
    body.pop(self_field, None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    obj[self_field] = hashlib.sha256(raw).hexdigest()
    return obj


def test_canonical_ai_node_admission_passes():
    assert verify_admission(load(PROFILE), load(ADMISSION))["running"] is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p, a: p.__setitem__("source_commit", "0" * 40),
        lambda p, a: p.__setitem__("integration_manifest_digest", "0" * 64),
        lambda p, a: p.__setitem__("nexus_artifact_sha256", "0" * 64),
        lambda p, a: p.__setitem__("network_transport_status", "BOUND"),
        lambda p, a: p.__setitem__("host_profile_status", "BOUND"),
        lambda p, a: p.__setitem__("supervisor_status", "MATERIALIZED"),
        lambda p, a: p.__setitem__("running", True),
        lambda p, a: p.__setitem__("auto_start", True),
        lambda p, a: p.__setitem__("financial_authority", "TREASURY"),
        lambda p, a: p.__setitem__("payment_authority", "METAPAY"),
        lambda p, a: p.__setitem__("blockchain_submission_authority", "SIGN_AND_SUBMIT"),
        lambda p, a: a.__setitem__("decision", "RUNNING"),
        lambda p, a: a.__setitem__("blockers", a["blockers"][1:]),
        lambda p, a: a.__setitem__("execution_authority", "ROOT"),
    ],
)
def test_fresh_hash_cannot_promote_authority_or_runtime(mutator):
    p, a = copy.deepcopy(load(PROFILE)), copy.deepcopy(load(ADMISSION))
    mutator(p, a)
    fresh_hash(p, "profile_digest")
    a["profile_digest"] = p["profile_digest"]
    fresh_hash(a, "admission_digest")
    with pytest.raises(AdmissionError):
        verify_admission(p, a)
