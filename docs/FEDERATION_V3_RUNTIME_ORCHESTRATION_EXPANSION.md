# Federation V3 — Meta-OS / Distributed Runtime expansion

Historical Part VIII described central, regional and local intelligent nodes. Meta-OS turns that idea into a verifiable runtime topology.

## Responsibilities

- node registry;
- host capability discovery;
- service placement;
- artifact/hash binding;
- startup/supervision/restart;
- health and readiness;
- version compatibility;
- resource/capability declarations;
- regional/domain topology;
- evidence for deployed/running state.

## State vocabulary

`REGISTERED → ADMITTED → LAUNCHABLE → RUNNING → HEALTHY → VERIFIED_RUNTIME`.

These states do **not** imply financial, signing or governance authority.

## Node hierarchy translation

Historical `central → regional → local` becomes a federation policy, not a single centralized control assumption:
- global coordination nodes;
- regional nodes;
- domain nodes;
- edge/local nodes;
- offline/store-forward nodes.

## Host/compute inputs

- `turbo_linux`: host/kernel/virtualization capabilities;
- `motherboard_xpu_xml`: optional compiled-graph compute capability;
- ordinary Linux/other supported hosts remain valid federation substrates.

## Transport

All cross-node messaging should use declared transport contracts from `synergynet` rather than hidden direct dependencies.

## Authority rule

`service_running != domain_authority`; Meta-OS may launch a service but may not grant that service payment/accounting/trading/state authority unless an explicit capability policy from the federation allows it.
