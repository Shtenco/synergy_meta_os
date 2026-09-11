# Legacy Keeper / GasGuard Sanitization V1

The legacy archive contains useful monitoring, pause, gas-guard and health-check ideas, but some generations also contain direct signing/deployment paths and embedded secret material.

Only the following concepts are reusable in Meta-OS:

```text
health observation
→ bounded policy evaluation
→ proposal / pause recommendation
→ explicit authorized executor
→ settlement/evidence
→ audit event
```

## Forbidden migration

- raw private keys or seed material;
- direct transaction signing in the supervisor;
- a network/UI/AI service gaining treasury rights because it is running;
- an automatic “gas-free” profitability claim from frozen execution or zero cost denominator;
- implicit fallback to live execution when configuration is incomplete.

## Required controls

- secret references only (Vault/KMS/HSM/MPC direction);
- least-privilege service capabilities;
- explicit execution role separate from health/monitor roles;
- transaction and daily limits;
- circuit breaker / guardian pause;
- signed node manifest and artifact hashes;
- deterministic health evidence;
- append-only audit events;
- staged update and rollback;
- fail-closed startup for financial execution capabilities.

A skipped/frozen transaction is an operational state, not economic profit.
