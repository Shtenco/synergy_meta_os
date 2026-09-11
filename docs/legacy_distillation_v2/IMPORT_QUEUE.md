# LEGACY DISTILLATION V2 — Import Queue

Canonical owner: `Shtenco/synergy_meta_os`

Nothing in this queue is auto-promoted to production. Every mechanism must pass the listed gate in this repository authority boundary.

| Priority | ID | Family | Action | Occurrences | Test gate | Representative |
|---|---|---|---|---:|---|---|
| P1_REWRITE | M097 | KEEPER_AUTOMATION_GAS | REWRITE_REQUIRED | 53 | `idempotency_budget_no_signing` | initKeeperFund |
| P1_REWRITE | M098 | KEEPER_AUTOMATION_GAS | REWRITE_REQUIRED | 44 | `idempotency_budget_no_signing` | setKeeperTopup |
| P1_PROMOTE_WITH_GATE | M095 | KEEPER_AUTOMATION_GAS | PROMOTION_CANDIDATE | 79 | `idempotency_budget_no_signing` | systemStop |
| P1_PROMOTE_WITH_GATE | M096 | KEEPER_AUTOMATION_GAS | PROMOTION_CANDIDATE | 55 | `idempotency_budget_no_signing` | DAOClosedRobotV2 |
| P1_PROMOTE_WITH_GATE | M099 | KEEPER_AUTOMATION_GAS | PROMOTION_CANDIDATE | 43 | `idempotency_budget_no_signing` | keeperFund |
| P1_PROMOTE_WITH_GATE | M100 | KEEPER_AUTOMATION_GAS | PROMOTION_CANDIDATE | 8 | `idempotency_budget_no_signing` | tick |
| P1_PROMOTE_WITH_GATE | M101 | KEEPER_AUTOMATION_GAS | PROMOTION_CANDIDATE | 6 | `idempotency_budget_no_signing` | AdaptiveBatchScheduler |
