# RESEARCH_COMPUTE_NODE profile consumer v1

This layer is the first explicit cross-root architecture contract consumed by Meta-OS.

Producer:

- `Shtenco/synergy_system`
- schema: `synergy.node-profile/v1`
- canonical profile digest: `406740705e853fa51ad4eacf7a01925fbe4b5cec491be35ea12ba777d217d714`

Consumer:

- `Shtenco/synergy_meta_os`

## Verification order

Meta-OS must perform the checks in this order:

1. verify the node-profile schema/shape/digest;
2. verify the Ed25519-signed `synergy.node-manifest/v1` identity envelope independently;
3. compare manifest capabilities and enabled service composition to the selected architecture profile;
4. reject any profile-forbidden capability/service even if the manifest was correctly re-signed;
5. only a `PROFILE_CONFORMANT` result may continue into existing artifact and lifecycle readiness checks.

## Exact research-node composition

Allowed capabilities:

- `CONTENT_CACHE`
- `NEXUS_COMPUTE`
- `P2P_RELAY`

Required enabled services:

- `content-cache` from `Shtenco/synergynet`;
- `nexus` from `Shtenco/agi_nexus`;
- `synergynet` from `Shtenco/synergynet`.

Forbidden service kinds:

- `AUTOPILOT`
- `BLOCKCHAIN`
- `FINANCIAL_OS`
- `METAPAY`

## Authority separation

Both profile and conformance result carry:

- `financial_authority = NONE`
- `payment_authority = NONE`
- `accounting_authority = NONE`
- `execution_authority = NONE`

`PROFILE_CONFORMANT` means only that a signed node manifest matches the selected architecture profile. It does not start processes, validate financial facts, execute payments, approve trades, or grant blockchain consensus rights.

## Important adversarial case

A manifest with `METAPAY_GATEWAY` can be perfectly validly signed by the node owner. The Ed25519 signature must still verify, while profile evaluation returns `SIGNED_BUT_PROFILE_NONCONFORMANT`.

This demonstrates the intended separation:

`identity != capability != architecture authorization != financial authority`.
