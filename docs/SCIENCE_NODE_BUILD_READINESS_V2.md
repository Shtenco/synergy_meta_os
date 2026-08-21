# SCIENCE_RESEARCH_NODE build readiness v2

This generation consumes the exact `synergy.node-build-lock/v2` source lock produced by `Shtenco/synergy_system` for `SCIENCE_RESEARCH_NODE`.

It deliberately separates four statements:

1. signed node identity is valid;
2. the signed manifest conforms to the exact Science Node profile;
3. the exact source-lock bytes are valid and pinned to the same profile/capability-registry generation;
4. reproducible build evidence exists for every service and the manifest artifact digest equals the verified build artifact digest.

The current canonical Science Node lock proves only (3) at the source-identity level. Every service is `SOURCE_CANDIDATE_NOT_BUILD_VERIFIED`, therefore the only valid readiness result is `BLOCKED_BUILD_EVIDENCE`.

A generic build-lock v2 object with a freshly recomputed hash is not admission authority. The current gate accepts only the exact pinned source-lock digest `24e4a3c6ed23c2e156b07821fb3b1e0e232651c256bc3b750d2ed25bee477757`. A later reproducibly built generation must introduce a new immutable build-lock/evidence generation and a new admission consumer.

`PROFILE_CONFORMANT`, valid source provenance, or future `BUILD_EVIDENCE_COMPLETE` do not start processes. `execution_authority` and `deployment_authority` remain `NONE`.
