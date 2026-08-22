# RESEARCH_COMPUTE_NODE build-plan consumer v1

Meta-OS independently consumes the architecture build plan produced by `Shtenco/synergy_system` and the exact domain build recipes produced by NEXUS and SynergyNet.

The consumer verifies:

- the source-lock is still valid and source-only;
- plan profile/source-lock bindings are exact;
- plan service IDs/repositories/source commits match the frozen research-node candidates;
- actual NEXUS and SynergyNet recipe bytes reproduce the digests referenced by the plan;
- all current recipes explicitly remain `NOT_REPRODUCIBLE_TOOLCHAIN_NOT_FROZEN`;
- no recipe or plan contains a build artifact digest;
- no object grants execution authority.

The only positive result in this generation is:

`BUILD_PLAN_CONFORMANT_NOT_REPRODUCIBLE`

with `deployable=false`.

This is deliberate. A correctly signed manifest, a valid node profile, a valid source-lock and a valid build plan are still insufficient to start a service until an additive build-evidence generation proves exact deployable artifact bytes under a frozen build toolchain.
