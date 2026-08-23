# AUTOPILOT V5 AI Node Production Bootstrap v2

Bootstrap v2 consumes Pre-Production RC2 and the new SynergyNet locator-availability negative evidence. It supersedes only the production-readiness assessment contract; Bootstrap v1 remains preserved historically.

Root:

`3e2f1eb8c34b3beba75157b88aedc13c354d4450b9c0ab611cd63bb51f4f9a8c`

## New hard blocker

Before any production start, a **new SynergyNet LocationEvidence v3** must exist. The old LocationEvidence v2 root is explicitly forbidden from being reused as v3.

The eight required fresh roots are:

1. new SynergyNet LocationEvidence v3;
2. persistent production HostProfile;
3. production SupervisorConfig;
4. fresh exact-artifact verification;
5. fresh health + transport roundtrip;
6. production DeploymentEvidence;
7. production DeploymentResult;
8. governance promotion evidence.

All eight must be distinct valid SHA-256 digests and may not reuse old SynergyNet LocationEvidence v2 or the LAB Host/Supervisor/DeploymentEvidence/DeploymentResult roots.

With missing inputs the evaluator returns:

`BLOCKED_MISSING_NEW_LOCATOR_AND_FRESH_PRODUCTION_INPUTS`.

Even after all eight roots are supplied it returns only:

`READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED`.

This generation never sets `startup_allowed=true`, never claims `current_running=true`, preserves NEXUS `network_access=NONE`, keeps outer-node networking operator-allowlisted and grants no financial/payment/accounting/blockchain-submission/node-execution authority.
