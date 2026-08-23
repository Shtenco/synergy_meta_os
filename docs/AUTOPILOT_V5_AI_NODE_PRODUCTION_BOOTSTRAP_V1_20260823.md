# AUTOPILOT V5 AI Node Production Bootstrap Contract v1

Root: `605c6c953e998efb9585a88c1c8f1a022d7160e3448139c2b80a33e6b6cbabd3`.

This generation turns the production transition gate into an executable **assessment** contract. It still cannot launch the node.

## Current state

The contract intentionally contains null production evidence roots. Running:

```bash
python scripts/assess_production_bootstrap_v1.py
```

must return `BLOCKED_MISSING_FRESH_PRODUCTION_INPUTS` and exit non-zero. This is the expected healthy behavior before a real persistent production host exists.

## Required fresh roots

The operator must later provide a JSON object containing seven distinct lowercase SHA-256 digests:

- `production_host_profile_digest`
- `production_supervisor_config_digest`
- `fresh_artifact_verification_digest`
- `fresh_health_transport_roundtrip_digest`
- `production_deployment_evidence_digest`
- `production_deployment_result_digest`
- `governance_promotion_digest`

The assessor rejects malformed roots, unknown fields, duplicate evidence roots and any direct reuse of the LAB HostProfile/Supervisor/DeploymentEvidence/DeploymentResult roots.

Even with all seven inputs present, the assessor returns only:

`READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED`.

`startup_allowed` remains false. Process start must belong to a future separate production deployment generation after independent verification of those evidence objects.

## Hard boundaries

- exact pre-production release: `717b473f…`
- exact DeploymentReference: `19375c02…`
- exact Production Transition Gate: `fd3f97c1…`
- NEXUS direct network access: `NONE`
- outer-node network: static operator allowlist only
- secrets: runtime provider only, never committed into repository/contracts
- auto-start: false
- current-running claim: false
- financial/payment/accounting/blockchain-submission/node-execution authority: `NONE`.
