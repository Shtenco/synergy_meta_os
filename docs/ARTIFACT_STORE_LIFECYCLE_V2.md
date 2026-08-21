# Meta-OS artifact store & lifecycle v2

V2 preserves the signed `synergy.node-manifest/v1` contract and adds a separate runtime planning layer.

## Artifact identity

`ArtifactStore` accepts bytes, computes SHA-256, and serves only content whose bytes still match the requested digest. A service is not startable merely because its manifest is signed: the exact artifact digest must exist locally and verify.

## Anti-rollback generation

`GenerationGuard` records the highest accepted generation per node and rejects:

- lower generations;
- different manifest bytes under the same generation number.

The in-memory guard is only a reference implementation. Production must persist the high-water mark atomically (TPM/NV, durable database, or equivalent monotonic state).

## Lifecycle planning

For each service the planner emits one of:

- `STARTABLE`
- `STOPPABLE`
- `UPGRADE_PENDING`
- `NOOP_RUNNING`
- `NOOP_STOPPED`
- `BLOCKED_CAPABILITY`
- `BLOCKED_ARTIFACT`

Every result carries `execution_authority=NONE`.

V2 deliberately does **not** call `subprocess`, shell commands, package managers or systemd. A later process adapter must use an allowlist of executable/artifact identities and least-privilege service accounts.
