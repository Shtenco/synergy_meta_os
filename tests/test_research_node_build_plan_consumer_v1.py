from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from synergy_meta_os.node_build_plan_consumer_v1 import (
    BuildPlanConsumerError,
    canonical_json,
    verify_research_node_build_plan_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _plan() -> dict:
    return _load("fixtures/node_build_plans/research_compute_node_build_plan_source_candidate_v1.json")


def _lock() -> dict:
    return _load("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")


def _recipes() -> dict[str, dict]:
    return {
        "Shtenco/agi_nexus": _load("fixtures/build_recipes/agi_nexus_build_recipe_v1.json"),
        "Shtenco/synergynet": _load("fixtures/build_recipes/synergynet_build_recipe_v1.json"),
    }


def test_build_plan_is_conformant_but_not_deployable() -> None:
    decision = verify_research_node_build_plan_v1(_plan(), _lock(), _recipes())
    assert decision.status == "BUILD_PLAN_CONFORMANT_NOT_REPRODUCIBLE"
    assert decision.source_lock_verified is True
    assert decision.domain_recipes_verified is True
    assert decision.reproducible is False
    assert decision.build_artifacts_verified is False
    assert decision.deployable is False


def test_plan_wire_schema_accepts_canonical_fixture() -> None:
    schema = _load("schemas/synergy_node_build_plan_v1.schema.json")
    jsonschema.validate(_plan(), schema)


def test_fresh_hash_cannot_promote_plan_to_build_verified() -> None:
    plan = copy.deepcopy(_plan())
    plan["services"][0]["build_artifact_digest"] = "aa" * 32
    plan["services"][0]["reproducibility_status"] = "REPRODUCIBLE"
    plan["plan_status"] = "BUILD_VERIFIED"
    body = dict(plan)
    body.pop("plan_digest", None)
    plan["plan_digest"] = hashlib.sha256(canonical_json(body)).hexdigest()
    with pytest.raises(BuildPlanConsumerError):
        verify_research_node_build_plan_v1(plan, _lock(), _recipes())


def test_self_consistent_recipe_upgrade_is_rejected_by_v1_consumer() -> None:
    recipes = _recipes()
    recipe = copy.deepcopy(recipes["Shtenco/agi_nexus"])
    recipe["build_toolchain"] = {"status": "FROZEN", "lock_digest": "bb" * 32}
    recipe["reproducibility_status"] = "REPRODUCIBLE"
    recipe["artifact_digest"] = "cc" * 32
    body = dict(recipe)
    body.pop("recipe_digest", None)
    recipe["recipe_digest"] = hashlib.sha256(canonical_json(body)).hexdigest()
    recipes["Shtenco/agi_nexus"] = recipe
    with pytest.raises(BuildPlanConsumerError):
        verify_research_node_build_plan_v1(_plan(), _lock(), recipes)


def test_changed_source_lock_bytes_are_rejected() -> None:
    source_lock = copy.deepcopy(_lock())
    source_lock["services"][0]["source_commit"] = "00" * 20
    with pytest.raises(Exception):
        verify_research_node_build_plan_v1(_plan(), source_lock, _recipes())
