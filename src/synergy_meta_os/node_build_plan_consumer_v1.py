from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from synergy_meta_os.node_build_lock_consumer_v1 import verify_research_node_source_lock_v1


class BuildPlanConsumerError(ValueError):
    pass


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_DIGEST = "406740705e853fa51ad4eacf7a01925fbe4b5cec491be35ea12ba777d217d714"
_SOURCE_LOCK_DIGEST = "14c763218602585d49e12060e1e6cf21d33815fda0cb18711a6522a26157ace2"
_PLAN_DIGEST = "809a23879e9e314b835956ef96cec8ede1faaeef1e5c2c06fd7330df600417aa"
_EXPECTED = {
    "content-cache": (
        "Shtenco/synergynet",
        "a8fde01c19420dbe63ca30e1da3b009c0c10064d",
        "1e885eefc5b244efb8e0b0031c88fbb85788677d655f3a595fa9a29b1645029a",
    ),
    "nexus": (
        "Shtenco/agi_nexus",
        "cbc06e83f7f9e242719667e446a090894e11eef1",
        "b262c98666843da80f37bcfae4d8b2105aa3b52b758a3a50406b198afc1a15be",
    ),
    "synergynet": (
        "Shtenco/synergynet",
        "a8fde01c19420dbe63ca30e1da3b009c0c10064d",
        "1e885eefc5b244efb8e0b0031c88fbb85788677d655f3a595fa9a29b1645029a",
    ),
}


def _check(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 2**53 - 1:
            raise BuildPlanConsumerError("unsafe integer")
        return
    if isinstance(value, float):
        raise BuildPlanConsumerError("floating point values are forbidden")
    if isinstance(value, list):
        for item in value:
            _check(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise BuildPlanConsumerError("object keys must be strings")
        for item in value.values():
            _check(item)
        return
    raise BuildPlanConsumerError("unsupported value")


def canonical_json(value: Any) -> bytes:
    _check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_without(payload: dict[str, Any], field: str) -> str:
    body = dict(payload)
    body.pop(field, None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


@dataclass(frozen=True)
class BuildPlanDecisionV1:
    status: str
    source_lock_verified: bool
    domain_recipes_verified: bool
    reproducible: bool
    build_artifacts_verified: bool
    deployable: bool
    blockers: tuple[str, ...]


def _verify_recipe(recipe: dict[str, Any], repository: str, source_commit: str, expected_digest: str) -> None:
    if not isinstance(recipe, dict) or recipe.get("schema") != "synergy.build-recipe/v1":
        raise BuildPlanConsumerError("invalid build recipe")
    if recipe.get("repository") != repository or recipe.get("source_commit") != source_commit:
        raise BuildPlanConsumerError("build recipe source identity mismatch")
    if recipe.get("recipe_digest") != expected_digest:
        raise BuildPlanConsumerError("build recipe reference mismatch")
    if _digest_without(recipe, "recipe_digest") != expected_digest:
        raise BuildPlanConsumerError("build recipe bytes do not match digest")
    if recipe.get("reproducibility_status") != "NOT_REPRODUCIBLE_TOOLCHAIN_NOT_FROZEN":
        raise BuildPlanConsumerError("v1 build recipe overclaims reproducibility")
    if recipe.get("artifact_digest") is not None:
        raise BuildPlanConsumerError("v1 build recipe cannot contain artifact digest")
    if recipe.get("execution_authority") != "NONE":
        raise BuildPlanConsumerError("build recipe grants execution authority")


def verify_research_node_build_plan_v1(
    plan: dict[str, Any],
    source_lock: dict[str, Any],
    recipes_by_repository: dict[str, dict[str, Any]],
) -> BuildPlanDecisionV1:
    verify_research_node_source_lock_v1(source_lock)
    if not isinstance(plan, dict) or set(plan) != {
        "schema", "plan_id", "profile_digest", "source_lock_digest", "services",
        "plan_status", "execution_authority", "plan_digest",
    }:
        raise BuildPlanConsumerError("unexpected build-plan shape")
    if plan["schema"] != "synergy.node-build-plan/v1":
        raise BuildPlanConsumerError("unexpected build-plan schema")
    if plan["plan_id"] != "RESEARCH_COMPUTE_NODE_BUILD_PLAN_SOURCE_CANDIDATE_20260822":
        raise BuildPlanConsumerError("unexpected build-plan id")
    if plan["profile_digest"] != _PROFILE_DIGEST:
        raise BuildPlanConsumerError("profile binding mismatch")
    if plan["source_lock_digest"] != _SOURCE_LOCK_DIGEST or source_lock["lock_digest"] != _SOURCE_LOCK_DIGEST:
        raise BuildPlanConsumerError("source-lock binding mismatch")
    services = plan["services"]
    if not isinstance(services, list) or services != sorted(services, key=lambda item: item.get("service_id", "")):
        raise BuildPlanConsumerError("services must be sorted")
    if len(services) != len(_EXPECTED):
        raise BuildPlanConsumerError("service set drifted")
    seen: set[str] = set()
    for service in services:
        fields = {
            "service_id", "repository", "source_commit", "build_recipe_digest",
            "build_artifact_digest", "reproducibility_status",
        }
        if not isinstance(service, dict) or set(service) != fields:
            raise BuildPlanConsumerError("unexpected service shape")
        sid = service["service_id"]
        if sid in seen or sid not in _EXPECTED:
            raise BuildPlanConsumerError("unexpected or duplicate service")
        seen.add(sid)
        repository, source_commit, recipe_digest = _EXPECTED[sid]
        if service["repository"] != repository or service["source_commit"] != source_commit:
            raise BuildPlanConsumerError("plan source identity drifted")
        if not _HEX40.fullmatch(service["source_commit"]):
            raise BuildPlanConsumerError("invalid source commit")
        if service["build_recipe_digest"] != recipe_digest or not _HEX64.fullmatch(service["build_recipe_digest"]):
            raise BuildPlanConsumerError("plan recipe reference drifted")
        if service["build_artifact_digest"] is not None:
            raise BuildPlanConsumerError("v1 plan cannot contain build artifact digest")
        if service["reproducibility_status"] != "NOT_REPRODUCIBLE_TOOLCHAIN_NOT_FROZEN":
            raise BuildPlanConsumerError("v1 plan overclaims reproducibility")
    if seen != set(_EXPECTED):
        raise BuildPlanConsumerError("service set incomplete")
    if plan["plan_status"] != "BUILD_PLAN_NOT_REPRODUCIBLE_YET":
        raise BuildPlanConsumerError("v1 plan overclaims readiness")
    if plan["execution_authority"] != "NONE":
        raise BuildPlanConsumerError("build plan grants execution authority")
    if plan["plan_digest"] != _PLAN_DIGEST or _digest_without(plan, "plan_digest") != _PLAN_DIGEST:
        raise BuildPlanConsumerError("build-plan digest mismatch")
    required_repositories = {entry[0] for entry in _EXPECTED.values()}
    if set(recipes_by_repository) != required_repositories:
        raise BuildPlanConsumerError("build recipe set incomplete")
    for repository in sorted(required_repositories):
        entries = [entry for entry in _EXPECTED.values() if entry[0] == repository]
        source_commits = {entry[1] for entry in entries}
        recipe_digests = {entry[2] for entry in entries}
        if len(source_commits) != 1 or len(recipe_digests) != 1:
            raise BuildPlanConsumerError("repository build identity is internally inconsistent")
        _verify_recipe(
            recipes_by_repository[repository],
            repository,
            next(iter(source_commits)),
            next(iter(recipe_digests)),
        )
    return BuildPlanDecisionV1(
        status="BUILD_PLAN_CONFORMANT_NOT_REPRODUCIBLE",
        source_lock_verified=True,
        domain_recipes_verified=True,
        reproducible=False,
        build_artifacts_verified=False,
        deployable=False,
        blockers=("BUILD_TOOLCHAIN_NOT_FROZEN", "BUILD_ARTIFACTS_NOT_VERIFIED"),
    )
