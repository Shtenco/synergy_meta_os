from runtime.archive_contracts import consume_archive_benchmark_evidence
import pytest

def test_benchmark_is_not_deployment_authority():
    x=consume_archive_benchmark_evidence({"benchmark_id":"b","target_sha256":"1"*64,"original_bytes":100,"container_bytes":80,"round_trip_verified":True,"temporal_cutoff_valid":True,"deployment_authority":False})
    assert x["deployment_authority"] is False

def test_benchmark_cannot_grant_deployment():
    with pytest.raises(ValueError):
        consume_archive_benchmark_evidence({"benchmark_id":"b","target_sha256":"1"*64,"original_bytes":100,"container_bytes":80,"round_trip_verified":True,"temporal_cutoff_valid":True,"deployment_authority":True})
