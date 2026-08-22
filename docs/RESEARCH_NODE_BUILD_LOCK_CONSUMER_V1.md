# RESEARCH_COMPUTE_NODE build-lock consumer v1

This layer consumes the exact `synergy.node-build-lock/v1` source-lock produced by `Shtenco/synergy_system` for the first cross-root research-compute node.

It intentionally separates three facts:

1. the node profile is architecture-conformant;
2. the selected source commits are frozen and match the source-lock;
3. deployable artifacts have been reproducibly built and verified.

V1 proves only the first two. The canonical source-lock contains `build_artifact_digest=null` for all services and has verification status `SOURCE_IDENTITY_FROZEN_BUILD_NOT_VERIFIED`.

Therefore a valid signed Meta-OS manifest plus a valid source-lock still yields:

- `source_identity_verified = true`
- `build_artifacts_verified = false`
- `deployable = false`
- blocker `BUILD_ARTIFACTS_NOT_VERIFIED`

A new digest cannot promote this generation to build-verified: the consumer independently requires null artifact digests and the exact source-only status. A later build-evidence generation must be additive and must bind reproducible build inputs to exact executable artifact digests before any process adapter may consume them.

This consumer grants no financial, payment, accounting or execution authority.
