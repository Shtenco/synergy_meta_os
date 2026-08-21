# Science Node admission decision v2

`synergy.node-admission-decision/v2` is a Meta-OS-derived audit object over four independently verified inputs:

1. capability registry;
2. signed node manifest v2;
3. SCIENCE_RESEARCH_NODE profile;
4. node build-lock v2.

The decision binds exact digests of all inputs plus evaluation time. It is re-verifiable from raw evidence.

For the current Science Node generation the only valid result is `BLOCKED_BUILD_EVIDENCE`, because all service entries remain `SOURCE_CANDIDATE_NOT_BUILD_VERIFIED` and have null build artifact/evidence digests.

Even a future `ADMISSION_REVIEWABLE` state grants no deployment or process execution authority. Actual artifact-store verification and least-privilege process activation remain separate Meta-OS gates.
