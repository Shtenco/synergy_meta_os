from __future__ import annotations

import copy, json
from pathlib import Path
import pytest

from synergy_meta_os.admission_v1 import AdmissionV1Error, digest, verify_admission_v1

ROOT=Path(__file__).resolve().parents[1]
def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
def bundle(): return load('admissions/research_compute_node_admission_v1.json'), load('evidence/research_compute_node_readiness_v4.json'), load('evidence/research_compute_node_build_plan_v4.json')

def test_canonical_admission_passes_without_starting():
    a,r,p=bundle(); out=verify_admission_v1(a,r,p)
    assert out['decision']=='ADMITTED_ARTIFACT_VERIFIED_NOT_RUNNING'
    assert out['running'] is False and out['auto_start'] is False
    assert out['execution_authority']=='NONE' and out['financial_authority']=='NONE'

def test_fresh_hash_cannot_admit_readiness_with_blocker():
    a,r,p=bundle(); r['blockers']=['INVENTED']; r['readiness_digest']=digest(r,'readiness_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)

def test_fresh_hash_cannot_swap_nexus_artifact():
    a,r,p=bundle(); p['services'][1]['artifact_digest']=p['services'][0]['artifact_digest']; p['plan_digest']=digest(p,'plan_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)

def test_admission_cannot_autostart_even_with_fresh_hash():
    a,r,p=bundle(); a['auto_start']=True; a['running']=True; a['admission_digest']=digest(a,'admission_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)

def test_admission_cannot_gain_execution_or_financial_authority():
    a,r,p=bundle(); a['execution_authority']='ROOT'; a['financial_authority']='TREASURY'; a['admission_digest']=digest(a,'admission_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)

def test_admission_cannot_change_network_authority():
    a,r,p=bundle(); a['network_authority_change']='ARBITRARY_EGRESS'; a['admission_digest']=digest(a,'admission_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)

def test_admission_is_pinned_to_exact_readiness_commit():
    a,r,p=bundle(); a['readiness_commit']='0'*40; a['admission_digest']=digest(a,'admission_digest')
    with pytest.raises(AdmissionV1Error): verify_admission_v1(a,r,p)
