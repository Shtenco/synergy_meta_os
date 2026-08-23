# Research Node artifact-location correction v2

Artifact identity/evidence and artifact location are independent claims.

After ArtifactRegistry v1 was written, the GitHub tree object that had been attached under the NEXUS artifact SHA-like filename was independently inspected. GitHub reports that blob `bb541be8b71ebad5977b3849e66e10224f0e1ded` is **15,009 bytes**, while the verified NEXUS BuildEvidence requires **56,967 bytes** for artifact SHA-256 `fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64`.

Therefore that location is rejected and MUST NOT be executed or treated as the verified NEXUS executable. The attachment is preserved as negative evidence rather than deleted.

Negative-evidence digest:

`81f7a4007a170ea3136d0ae936b4c8bd8b82c3bc36201de0c9cd2d816a4d21d8`

Corrected canonical roots:

- ArtifactRegistry v2: `46809f10fd648ad24bf002c54708cd977eaaab8b1d65486a2f0fdb505140de7c`
- DeploymentPlan v2: `381ac687eeff4b771c3cf18900b4485325bd98be7995c6982a251e68074c72f6`

Both NEXUS and SynergyNet are now conservatively `RECONSTRUCTABLE_ONLY` until exact binary bytes are published to a durable locator and re-hashed from that locator.

DeploymentPlan v2 remains `BLOCKED_NOT_LAUNCHABLE` with exactly five blockers:

1. `NEXUS_ARTIFACT_LOCATION_NOT_DURABLE`
2. `SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE`
3. `HOST_PROFILE_NOT_BOUND`
4. `SUPERVISOR_CONFIG_NOT_MATERIALIZED`
5. `DEPLOYMENT_EVIDENCE_NOT_EXECUTED`

This correction does **not** invalidate Readiness v4 or Admission v1: those prove build reproducibility and artifact identity/evidence, not durable deployment location. It does invalidate the v1 claim that the NEXUS binary location was resolvable.
