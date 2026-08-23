# AUTOPILOT V5 AI Node Production Bootstrap v4

Bootstrap v4 is the final fail-closed contract layer before binding a **real persistent production host**. It consumes the federation-aligned Pre-Production RC4 and pins the current exact artifact/transport/admission lineage.

## Canonical roots
- Pre-Production RC4: `a7239ebf88b07f41b390120e3b3e23448e28548b3b9d981eb80a1fc014325803`
- Federation Registry v3: `af24fe8c4b3ddfd8832f7e5ac6d92b2d4d69761cb9ab869407cd4d085e475526`
- Meta-OS Profile v3: `96ea31f50ff61b478390d682e88cca89c806e88dbaef1c4fc53b109724ca8222`
- Meta-OS Admission v3: `b1c151d4d5095278006d338c65f3a56b4853c3b3aa70a429205bea84fc5770e8`
- SynergyNet LocationEvidence v3: `b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220`
- SynergyNet TransportBinding v2: `0c58185ea0af4a8abc7ce215c0b7ff077cea9357e831b9d197ec730a34ed6c7e`
- Bootstrap v4: `39d262d4d6b28ceba3f6ffacadebd79d023e214ba63db6dbef6f5a3ad15547c6`

## Irreducible production inputs
A production promotion requires seven fresh evidence roots generated from one real persistent production lifecycle:
1. production HostProfile;
2. production SupervisorConfig;
3. fresh artifact verification;
4. fresh health + SynergyNet transport roundtrip;
5. production DeploymentEvidence;
6. production DeploymentResult;
7. explicit governance promotion evidence.

The evaluator rejects malformed/duplicate roots and direct reuse of historical LAB HostProfile, SupervisorConfig, DeploymentEvidence or DeploymentResult.

Even with all seven roots present, Bootstrap v4 **does not launch the node**. It can only reach `READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED`. A separate governance-verified production generation must authorize and record any actual persistent start.

## Required artifact preflight on the real host
Before process start, fresh verification must prove:
- AUTOPILOT release ZIP SHA-256 `afba4eb7508564292f6695dbef69e9a043a998da8a2e4b587922c17bbefb37cb`, size `1,045,560`;
- embedded exact NEXUS SHA-256 `e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325`, size `56,965`;
- SynergyNet resolved through LocationEvidence v3 and reconstructed as SHA-256 `7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7`, size `12,837`.

No secrets, credentials or invented server facts belong in repository evidence. Secrets are runtime-provider-only. NEXUS retains direct network access `NONE`; outer-node networking remains static operator allowlist only. Financial/payment/accounting/host-execution/blockchain-submission/node-execution authority remains `NONE` in this bootstrap contract.
