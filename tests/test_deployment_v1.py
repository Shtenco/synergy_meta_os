from __future__ import annotations

import copy, json
from pathlib import Path
import pytest

from synergy_meta_os.admission_v1 import digest
from synergy_meta_os.deployment_v1 import DeploymentV1Error, verify_artifact_registry_v1, verify_deployment_plan_v1

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def bundle(): return load('registry/research_compute_node_artifact_registry_v1.json'), load('deployments/research_compute_node_deployment_plan_v1.json')

def test_canonical_registry_is_partial_and_deployment_blocked():
    r,p=bundle(); verify_artifact_registry_v1(r); out=verify_deployment_plan_v1(p,r)
    assert r['blockers']==['SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE']
    assert out['deployment_status']=='BLOCKED_NOT_LAUNCHABLE'
    assert out['running'] is False and out['auto_start'] is False

def test_nexus_locator_cannot_be_substituted_with_fresh_hash():
    r,p=bundle(); r['entries'][0]['git_blob']='0'*40; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_synergynet_location_cannot_be_falsely_promoted():
    r,p=bundle(); r['entries'][1]['locator_status']='DURABLE_GIT_TREE_PATH'; r['entries'][1]['availability_status']='RESOLVABLE'; r['blockers']=[]; r['registry_status']='COMPLETE_LOCATION_COVERAGE'; r['registry_digest']=digest(r,'registry_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_host_binding_cannot_be_invented():
    r,p=bundle(); p['host_binding_status']='BOUND'; p['host_profile_digest']='1'*64; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_process_cannot_be_marked_started():
    r,p=bundle(); p['processes'][0]['planned_state']='RUNNING'; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_nexus_cannot_gain_network_policy():
    r,p=bundle(); p['processes'][0]['network_policy']='ARBITRARY_EGRESS'; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_deployment_blockers_cannot_be_erased():
    r,p=bundle(); p['blockers']=[]; p['deployment_status']='LAUNCHABLE'; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)

def test_deployment_cannot_gain_authority_or_autostart():
    r,p=bundle(); p['execution_authority']='ROOT'; p['financial_authority']='TREASURY'; p['running']=True; p['auto_start']=True; p['deployment_digest']=digest(p,'deployment_digest')
    with pytest.raises(DeploymentV1Error): verify_deployment_plan_v1(p,r)
