from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_node_build_lock_fixture_matches_wire_schema() -> None:
    schema = json.loads((ROOT / "schemas/synergy_node_build_lock_v1.schema.json").read_text())
    payload = json.loads((ROOT / "fixtures/node_build_locks/research_compute_node_source_candidate_v1.json").read_text())
    jsonschema.validate(payload, schema)


def test_execution_authority_is_closed_to_none() -> None:
    schema = json.loads((ROOT / "schemas/synergy_node_build_lock_v1.schema.json").read_text())
    payload = json.loads((ROOT / "fixtures/node_build_locks/research_compute_node_source_candidate_v1.json").read_text())
    payload = copy.deepcopy(payload)
    payload["execution_authority"] = "PROCESS_EXECUTION"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
