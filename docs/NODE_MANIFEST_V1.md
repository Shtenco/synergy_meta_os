# SYNERGY Meta-OS signed node manifest v1

## Purpose

Bind one node identity to an explicit capability set and exact service artifacts before any runtime adapter is allowed to start processes.

```text
signed manifest
→ signature verification
→ expiry / generation / canonical-byte checks
→ capability checks
→ desired service-state decisions
→ future allowlisted process adapter
```

V1 stops before process execution. `RUNNABLE` means the manifest permits the service; it does not mean a subprocess was started.

## Capability isolation

Examples:

- `P2P_RELAY` does not imply `BLOCKCHAIN_VALIDATOR`;
- `BLOCKCHAIN_VALIDATOR` does not imply `FINANCIAL_SERVICE`;
- `NEXUS_COMPUTE` does not imply `METAPAY_GATEWAY`;
- host/root privilege does not create economic authority.

Each service binds an exact repository plus SHA-256 artifact digest. A different binary/config generation requires a new signed manifest generation.

## Signature generation

V1 implements Ed25519 as a bootstrap identity signature because it is widely available and independently verifiable. It is **not** the final post-quantum node-identity design.

A future immutable manifest generation should introduce ML-DSA or a classical+PQ hybrid signature profile with downgrade protection. V1 must not be silently reinterpreted as PQ-secure.

## Process execution boundary

Future execution adapters must not accept arbitrary shell strings from the manifest. They should resolve `(repository, artifact_digest, service kind)` through an allowlisted local artifact store and launch under least-privilege OS/capability identities.
