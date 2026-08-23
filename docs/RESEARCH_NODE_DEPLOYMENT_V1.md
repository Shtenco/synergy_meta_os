# Research Compute Node — Artifact Registry and Deployment v1

Admission v1 proves registry eligibility. It does not prove that executable bytes are durably locatable on every required domain or that a real host is bound.

This additive generation introduces that next boundary.

## Artifact Registry v1

Canonical digest:

`8ecec30555e8a2a7930549b2e67583c2ea1fb90a422e6ed6523a5d8e01ff2d49`

NEXUS is now durably tree-addressable in `Shtenco/agi_nexus`:

- artifact SHA-256: `fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64`
- commit: `a47840e6c76b3eefcc5b0053317f5219682e9ee1`
- path: `artifacts/fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64.pyz`
- Git blob: `bb541be8b71ebad5977b3849e66e10224f0e1ded`
- location state: `RESOLVABLE`

SynergyNet remains reproducibly rebuildable and artifact-verified, but its exact binary bytes are not yet attached to a durable repository/content-store locator. Its location state therefore remains `RECONSTRUCTABLE_ONLY`.

Registry blocker:

`SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE`

## DeploymentPlan v1

Canonical digest:

`dd66bef640aba79aa9055c590e6126c541b59f9f909ee033fc7b1982c4505c14`

The plan is intentionally host-unbound and non-launchable. Remaining blockers are exactly:

1. `SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE`
2. `HOST_PROFILE_NOT_BOUND`
3. `SUPERVISOR_CONFIG_NOT_MATERIALIZED`
4. `DEPLOYMENT_EVIDENCE_NOT_EXECUTED`

Canonical state:

- `deployment_status = BLOCKED_NOT_LAUNCHABLE`
- `running = false`
- `auto_start = false`
- `execution_authority = NONE`
- `financial_authority = NONE`

NEXUS keeps `NO_NETWORK`. Content-cache may only bind an operator-selected local host/store. Relay may only use an operator-local static allowlist. No deployment contract grants remote filesystem selection or financial authority.

The next generation may only become launchable after durable SynergyNet artifact publication, an exact host profile, materialized supervisor configuration and executed host-specific deployment/health evidence.
