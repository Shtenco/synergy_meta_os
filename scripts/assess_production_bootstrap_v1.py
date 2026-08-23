from __future__ import annotations

import argparse
import json
from pathlib import Path

from synergy_meta_os.production_bootstrap_v1 import assess_production_inputs, load_default_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess SYNERGY AUTOPILOT V5 AI-node production bootstrap readiness. This tool never starts processes.")
    parser.add_argument("--inputs", type=Path, help="Optional JSON object mapping the seven required production input names to fresh SHA-256 digests.")
    args = parser.parse_args()

    supplied = None
    if args.inputs:
        supplied = json.loads(args.inputs.read_text(encoding="utf-8"))
        if not isinstance(supplied, dict):
            raise SystemExit("--inputs must contain a JSON object")

    result = assess_production_inputs(load_default_contract(), supplied)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"].startswith("READY_FOR_") else 23


if __name__ == "__main__":
    raise SystemExit(main())
