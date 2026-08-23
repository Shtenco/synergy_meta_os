# AUTOPILOT V5 AI Node Production Bootstrap v3

Bootstrap v3 consumes Pre-Production RC3 and pins the remediated SynergyNet LocationEvidence v3 as an already satisfied prerequisite.

Roots:
- Bootstrap v2: `3e2f1eb8c34b3beba75157b88aedc13c354d4450b9c0ab611cd63bb51f4f9a8c`
- Pre-Production RC3: `be8ca90e514e72ddccdc67a38cdd9b8321c2b55eb17ba6f04a9c65dbd4a16129`
- SynergyNet LocationEvidence v3: `b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220`
- Bootstrap v3: `00330d77273e5dd35ef7ba30cfe02a4cc4aef89522e374d1fb2ef833c318aa75`

The durable-locator blocker is removed. Exactly seven fresh production inputs remain: persistent HostProfile, production SupervisorConfig, fresh artifact verification on that host, fresh health/transport roundtrip, production DeploymentEvidence, production DeploymentResult and explicit governance promotion.

Default state is fail-closed and not running. Even with all seven inputs supplied, the evaluator returns only `READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED`; it never starts processes. Historical LAB Host/Supervisor/Deployment roots are forbidden as production evidence.

NEXUS direct network access remains `NONE`; outer-node networking remains static operator allowlist only; secrets remain runtime-provider-only; all financial/payment/accounting/blockchain-submission/node-execution authority remains `NONE`.
