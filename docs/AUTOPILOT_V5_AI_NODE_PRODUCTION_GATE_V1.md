# AUTOPILOT V5 AI Node — Production Transition Gate v1

The node has executed successfully in an ephemeral LAB, but LAB evidence is not reusable as production evidence.

Gate root: `fd3f97c1422376ae507e7ec0ab1dcff529cba4ad9b5f6b1e9b7b62ef43d75b8c`.

Current state:
- LAB result: `011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833`
- LAB state: `RUNNING_VERIFIED_THEN_STOPPED_GRACEFULLY`
- current running: false
- production: `BLOCKED_NOT_DEPLOYED`

Production requires a **new** persistent HostProfile, a **new** production SupervisorConfig, fresh artifact resolution/hash verification, a fresh health + SynergyNet roundtrip, fresh DeploymentEvidence/Result, and explicit governance promotion.

It is explicitly forbidden to reuse LAB PIDs, timestamps, HostProfile, SupervisorConfig or DeploymentEvidence as production evidence. The verifier keeps production evidence fields null in this blocked generation and rejects a fresh-hash attempt to populate them.

NEXUS remains network-isolated. Auto-start and all financial/payment/accounting/blockchain/node execution authority remain NONE.
