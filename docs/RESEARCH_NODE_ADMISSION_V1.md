# Research Compute Node — Meta-OS Admission v1

This is the first Meta-OS admission contract for the Research Compute Node.

It consumes exact mirrored `synergy.node-build-plan/v4` and `synergy.node-readiness/v4` evidence from `Shtenco/synergy_system` and is pinned to readiness commit `c2ec96ef24a39d397f0903f5a7f5ef7e96e46865`.

Canonical roots:

- Readiness v4: `ee20353d76d377f31f8054dae0c6463db4b3aae1a57b4ccfc2d7631e2251a95b`
- BuildPlan v4: `8f37d84645e78818b17c884e7c46d1ba680e79a53a2125faab64de42a290953f`
- ToolchainLock: `af92c9f1909ae3b64aaea78bdce2c6d05deb974ad242482b36e0c8ce820a2848`
- ArtifactSet: `14a67cfbe75361a8ca2f3bd43befd3aef97eddc29d4d725bd83f289ed829bc77`
- Admission v1: `4ace5623bc0a3100e2502132056f76821eda930199eb74498cc1cbe4f4008e37`

Decision: `ADMITTED_ARTIFACT_VERIFIED_NOT_RUNNING`.

The admission effect is deliberately only `REGISTRY_ELIGIBILITY_ONLY`. It does not launch processes, choose host ports or filesystem paths, grant network egress, grant financial authority, or grant execution authority. Canonical values remain:

- `running=false`
- `auto_start=false`
- `execution_authority=NONE`
- `financial_authority=NONE`
- `network_authority_change=NONE`

A later deployment generation must be a separate explicit transition with its own host-specific evidence and authority review. Admission is not deployment.
