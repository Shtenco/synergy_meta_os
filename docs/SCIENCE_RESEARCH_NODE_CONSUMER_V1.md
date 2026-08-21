# SCIENCE_RESEARCH_NODE consumer v1

Meta-OS independently consumes the exact `SCIENCE_RESEARCH_NODE` profile and verifies it against a signed `synergy.node-manifest/v2` plus the exact capability registry bytes.

Three independent statements are checked:

1. the capability registry is valid and pinned by digest;
2. the manifest signature and manifest bytes are valid;
3. the manifest service/capability composition exactly matches the science-node profile.

A correctly signed manifest that adds MIDAS, MetaPay, Financial OS, blockchain or autopilot remains cryptographically valid but is `SIGNED_BUT_PROFILE_NONCONFORMANT`.

Profile conformance grants no process execution, financial, payment, accounting, trading or scientific-truth authority. Build/readiness/admission remain separate gates.
