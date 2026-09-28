from runtime.app_release_contracts import consume_store_source_evidence,consume_superapp_surface
import pytest
def test_store_source_not_build_or_publish():
    p={"app_id":"ai.sinergy.finance","version":"8.1.0","android_gradle_sha256":"1"*64,"android_manifest_sha256":"2"*64,"ios_project_sha256":"3"*64,"ios_privacy_sha256":"4"*64,"source_verified":True,"artifact_built":False,"store_published":False,"deployment_authority":False}
    x=consume_store_source_evidence(p);assert x["artifact_built"] is False
def test_superapp_surface_not_deployed():
    p={"name":"SINERGY Node","start_url":"/index.html","manifest_sha256":"1"*64,"index_sha256":"2"*64,"android_gradle_sha256":"3"*64,"android_wrapper_sha256":"4"*64,"source_surface_verified":True,"android_artifact_built":False,"deployment_authority":False}
    x=consume_superapp_surface(p);assert x["deployment_authority"] is False
def test_source_cannot_self_promote():
    p={"app_id":"x","version":"1","android_gradle_sha256":"1"*64,"android_manifest_sha256":"2"*64,"ios_project_sha256":"3"*64,"ios_privacy_sha256":"4"*64,"source_verified":True,"artifact_built":True,"store_published":False,"deployment_authority":False}
    with pytest.raises(ValueError): consume_store_source_evidence(p)
