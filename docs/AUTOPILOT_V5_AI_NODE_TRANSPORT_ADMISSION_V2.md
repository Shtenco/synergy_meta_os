# AUTOPILOT V5 AI Node — Transport-bound Admission v2

This generation consumes SynergyNet transport binding `3c8198e10863c52c0492ca422c404a1e05e6fd2f48f4c393587d9d87eee3855f` and removes only `SYNERGYNET_TRANSPORT_NOT_BOUND` from the prior AI-node admission.

Profile v2: `6a84a2dd132823756c9f159b04584ac384dca9514316b3ff5c9f4ce06e1696d3`.
Admission v2: `4d3502dba28745b8a734c082ca0260cbbfd4ead11a1396537434844df9987ee3`.

Remaining blockers are exactly:
- `HOST_PROFILE_NOT_BOUND`
- `SUPERVISOR_CONFIG_NOT_MATERIALIZED`
- `DEPLOYMENT_EVIDENCE_NOT_EXECUTED`

The outer AUTOPILOT node owns the bounded transport binding; embedded NEXUS remains `network_access=NONE`. Host address/port are still not materialized. `running=false`, `auto_start=false`; financial/payment/accounting/host/blockchain/execution authority remain `NONE`.
