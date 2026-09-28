from runtime.change_contracts import require_deployable_change
import pytest


def test_meta_os_requires_approved_passing_change():
    require_deployable_change({
        "repository":"Shtenco/demo",
        "review_status":"APPROVED",
        "requirements":["REQ-1"],
        "checks":[{"name":"pytest","status":"PASS"}],
        "artifact_sha256":"1"*64,
    },expected_repository="Shtenco/demo")


def test_meta_os_rejects_failed_change():
    with pytest.raises(ValueError):
        require_deployable_change({
            "repository":"Shtenco/demo",
            "review_status":"APPROVED",
            "requirements":["REQ-1"],
            "checks":[{"name":"pytest","status":"FAIL"}],
        })
