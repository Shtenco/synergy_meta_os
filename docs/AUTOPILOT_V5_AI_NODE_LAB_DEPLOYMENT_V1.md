# AUTOPILOT V5 AI Node — Executed LAB Deployment v1

This generation records a real local execution of the AUTOPILOT V5 + exact NEXUS + SMM AI node together with the exact SynergyNet runtime artifact.

## Bound roots

- AI node integration root: `a793250aaa2299fdaf1661e985423c2b62687a19395ceabcc7bb63c005defe54`
- SynergyNet transport binding: `3c8198e10863c52c0492ca422c404a1e05e6fd2f48f4c393587d9d87eee3855f`
- HostProfile: `36a9092977e360b56fd7d1e21b4504f1215ed741df6f492b3ed37b79649573bb`
- SupervisorConfig: `74797e02e0bb32722bbfffb76af42bb00d495fb3a5c0ea4a5b48a4e1d4275879`
- DeploymentEvidence: `8e1b05dca7e349d57e1908dca717d2c1d451ca79adde5cfe539e9e46f83d052b`
- DeploymentResult: `011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833`

## What actually executed

Four live processes were started on the ephemeral Linux/x86_64 lab host:

1. AUTOPILOT/NEXUS resident;
2. SynergyNet content-cache A;
3. SynergyNet content-cache B;
4. SynergyNet relay.

The exact SynergyNet artifact was independently reconstructed from the published source/build contract and matched SHA-256 `7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7`, size 12,837 bytes, manifest `fde462820a5d8a1b8c48c565a1ccd5fa3a72a9f36a2deec5305af3ce021d4de6`.

During the captured running snapshot all four PIDs were alive. AUTOPILOT resident and exact NEXUS returned READY. Both content caches and relay returned READY. A 45-byte chunk was PUT into cache A, routed through the exact relay, read from cache B and hash-verified at the destination.

After evidence capture every process received graceful SIGTERM and exited with code 0.

## Claim boundary

This proves **local LAB running**, not a persistent production deployment. The canonical result therefore states:

- `running_snapshot_status = RUNNING_VERIFIED`
- `final_state = STOPPED_AFTER_VERIFICATION`
- `current_running = false`
- `production_status = NOT_RUNNING_NO_PERSISTENT_PRODUCTION_HOST`

A future persistent deployment must bind a real production host and production supervisor and generate fresh deployment evidence. It may not simply relabel this LAB evidence.

NEXUS network access remains NONE. AI node financial/payment/accounting/blockchain submission authority remains NONE. The only host-side authority used was the bounded LAB supervisor needed to start and stop the exact pinned processes.
