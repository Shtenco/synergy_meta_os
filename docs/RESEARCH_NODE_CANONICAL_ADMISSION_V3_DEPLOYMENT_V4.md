# Research Compute Node — canonical Admission v3 / Registry v4 / Deployment v4

This generation is additive. Admission v1/v2, ArtifactRegistry v1-v3 and DeploymentPlan v1-v3 remain immutable historical evidence.

## Upstream root

Meta-OS now admits only `Shtenco/synergy_system` Readiness v6:

- readiness commit: `349c8d506be14043b120be868851117990855d26`
- Readiness v6: `6714beff9f366ed19c6b000b9239afffcd797cfc9d3fc4319b70a8af53b9af1f`
- BuildPlan v7: `46a4ee4c01fba5fb8c5e3cff51b4f6b5e7090347ef1ec1ab6763a606a31aaa2e`
- ArtifactSet v4: `d479b71a0756288b5d8d6d7d7433881cbd448a63c22bc9f87f271df7f82479c2`

The former v5/v2/v3 chain depended on first-generation artifact-location evidence envelopes whose self-digest fields failed canonical re-hash. They are retained as negative/superseded evidence, not repaired in place.

Canonical location evidence:

- NEXUS v2: `341989039238b9735018bad71c2ac1f0114ae15b4736faa524b5f7a643c27f47`
- SynergyNet v2: `c4102a8e668b79fc961a5f1767154154f4a600d320442770d74c7a006a5cee08`

Each resolver must fetch by connected Drive file ID and then verify artifact SHA-256 and byte size before execution.

## Meta-OS roots

- Admission v3: `e16e9c0334ed0dcd61aeac0ac1044139ec735c3fcbea92bb1eb55b171bfbb13e`
- ArtifactRegistry v4: `a67257b09688d08c6ddf39c0bed9847677de57df79c08d40a2e6bcc67e260960`
- DeploymentPlan v4: `911e15e9b9913c6201d6a034654aac336f8bbf298b7d720b9c9f987dced51d7c`

Admission remains registry eligibility only. It grants no process start, network expansion, financial authority, payment authority or accounting authority.

## Deployment boundary

Artifact-location blockers are resolved. Deployment v4 is nevertheless `BLOCKED_NOT_LAUNCHABLE` with exactly:

1. `HOST_PROFILE_NOT_BOUND`
2. `SUPERVISOR_CONFIG_NOT_MATERIALIZED`
3. `DEPLOYMENT_EVIDENCE_NOT_EXECUTED`

All processes are `NOT_STARTED`. NEXUS remains `NO_NETWORK`. `running=false` and `auto_start=false`.

This creates the explicit law:

`ADMITTED != LAUNCHABLE != RUNNING`.

The next Compute-OS generation may bind a real host profile, but must not remove supervisor or executed-deployment-evidence blockers until those exact facts exist.

## Economic authority boundary

Compute OS may produce evidence and computational results. It cannot authorize or post economic actions.

- Financial OS owns accounting/NAV/profit/distribution capacity and authorization.
- MetaPay owns settlement execution/evidence under explicit Financial OS handoff.
- Meta-OS owns node admission/supervision only.
- NEXUS owns reasoning only.
- SynergyNet owns transport/cache/relay only.

No field in this generation permits NEXUS, SynergyNet or Meta-OS to spend funds, recognize profit, post ledger entries or mint payment authority.
