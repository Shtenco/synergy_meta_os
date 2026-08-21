# Node Admission Decision v2 — SCIENCE_RESEARCH_NODE

`synergy.node-admission-decision/v2` is an append-only Meta-OS audit artifact built from exact raw evidence:

- signed `synergy.node-manifest/v2`;
- exact `synergy.capability-registry/v1`;
- exact `SCIENCE_RESEARCH_NODE` profile;
- exact pinned `synergy.node-build-lock/v2` source generation;
- evaluation time.

The current Science Node source lock contains immutable service source identities but no reproducibly verified build artifacts. Therefore the canonical decision is `BLOCKED_BUILD_EVIDENCE` with four `BUILD_NOT_VERIFIED:*` blockers.

The canonical decision digest is:

`d33c013bd28feee1faea62a3521da40fa6a532285ffce81a59819424cf0a7156`

A fresh outer hash cannot change the decision into ADMITTED, grant deployment authority, or grant scientific-truth authority: the verifier rebuilds the decision from raw signed manifest/profile/registry/build-lock evidence at the recorded evaluation time.

V2 intentionally has no admitted state. A future build-verified deployment generation must be a new admission version bound to a new immutable evidence-bearing build lock.
