# LEGACY DISTILLATION V3 — synergy_meta_os

Assigned primitives:

- P032 KEEPER_AUTOMATION_GAS — REWRITE — 6 mechanisms / 282 occurrences.
- P033 KEEPER_AUTOMATION_GAS — PROMOTE — 1 mechanism / 6 occurrences.

Required gates: idempotent keeper actions, explicit gas/budget ceilings, retry safety, failure isolation and zero raw signing secrets in orchestration. Keeper-triggered mint/QE cannot increase treasury truth without a balanced counter-entry and Financial OS reconciliation.
