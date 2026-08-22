from __future__ import annotations

import json
from pathlib import Path
import pytest

from synergy_meta_os.admission_v1 import digest
from synergy_meta_os.deployment_v1 import DeploymentV1Error
from synergy_meta_os.deployment_v2 import verify_artifact_registry_v2, verify_deployment_plan_v2

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def bundle(): return load('registry/research_compute_node_artifact_registry_v2.json'), load('deployments/research_compute_node_deployment_plan_v2.json')

def test_corrected_registry_and_deployment_pass_fail_closed():
    r,p=bundle(); verify_artifact_registry_v2(r); out=verify_deployment_plan_v2(p,r)
    assert r['registry_status']=='NO_VERIFIED_DURABLE_BINARY_LOCATIONS'
    assert out['deployment_status']=='BLOCKED_NOT_LAUNCHABLE'
    assert out['running'] is False and out['auto_start'] is False

def test_negative_evidence_cannot_be_omitted_with_fresh_hash():
    r,p=bundle(); r['negative_evidence_digests']=[]; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_rejected_nexus_locator_cannot_be_repromoted():
    r,p=bundle(); n=r['entries'][0]; n['locator_status']='DURABLE_GIT_TREE_PATH'; n['availability_status']='RESOLVABLE'; r['blockers']=['SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE']; r['registry_status']='PARTIAL_LOCATION_COVERAGE'; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_rejected_locator_size_cannot_be_rewritten():
    r,p=bundle(); r['entries'][0]['rejected_locator']['observed_size']=56967; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_synergynet_build_input_is_pinned():
    r,p=bundle(); r['entries'][1]['build_input_digest']='0'*64; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_deployment_cannot_erase_location_blockers():
    r,p=bundle(); p['blockers']=['HOST_PROFILE_NOT_BOUND','SUPERVISOR_CONFIG_NOT_MATERIALIZED','DEPLOYMENT_EVIDENCE_NOT_EXECUTED']; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_nexus_still_has_no_network_and_not_started():
    r,p=bundle(); p['processes'][0]['network_policy']='ARBITRARY_EGRESS'; p['processes'][0]['planned_state']='RUNNING'; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)

def test_host_or_authority_cannot_be_invented():
    r,p=bundle(); p['host_binding_status']='BOUND'; p['host_profile_digest']='1'*64; p['running']=True; p['auto_start']=True; p['execution_authority']='ROOT'; p['financial_authority']='TREASURY'; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v2(p,r)
