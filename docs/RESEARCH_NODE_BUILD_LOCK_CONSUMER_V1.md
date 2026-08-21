# Research Node source build-lock consumer v1

This layer consumes `synergy.node-build-lock/v1` produced by `Shtenco/synergy_system`.

The canonical v1 lock binds the `RESEARCH_COMPUTE_NODE` profile to exact source commits, but intentionally carries no built artifact digest. Meta-OS therefore treats it as source provenance only.

Readiness semantics:

`PROFILE_CONFORMANT + SOURCE_LOCK_CONFORMANT + BUILD_EVIDENCE_MISSING = NOT_DEPLOYABLE`.

This is deliberate. A Git commit is not an executable artifact. A manifest may contain arbitrary artifact digests, but until a producer-side reproducible build receipt proves that those bytes were built from the locked source revision, Meta-OS must not treat the source lock as build evidence.

The consumer verifies:

- exact profile digest;
- exact repository and immutable source commit per service;
- exact source role/ref metadata for this frozen candidate generation;
- no non-null `build_artifact_digest` in the source-only v1 generation;
- no execution authority;
- manifest service repositories agree with the lock.

Future deployability requires a separate build-receipt generation plus exact artifact bytes in the Meta-OS ArtifactStore. This v1 source lock can never be upgraded in place into a build receipt.
