# Node Admission Decision v1

`synergy.node-admission-decision/v1` is an append-only audit artifact produced by Meta-OS after independently checking a signed node manifest against the federation node profile and the exact source build lock.

It is intentionally **not** an execution ticket.

For the current `RESEARCH_COMPUTE_NODE` generation the source lock contains immutable NEXUS/SynergyNet source commits but no reproducibly built service artifact digests. Therefore a valid decision is expected to be:

- `PROFILE_CONFORMANT`
- `SOURCE_LOCK_CONFORMANT`
- `BUILD_EVIDENCE_MISSING`
- `BLOCKED_BUILD_EVIDENCE`

The canonical blocked decision digest is:

`cac0a7dca9ac1c304ca9d37577d32c95024de02edf4c70f283d5474ddfcbb9a1`

## Why a negative decision is an artifact

Fail-closed behavior must be explainable and auditable. A missing process start is ambiguous; an admission decision explicitly records the exact manifest/profile/source-lock identities and the blockers that prevented admission.

## Historical verification

A decision is verified against the signed manifest at the original `evaluated_at` time. Expiration of that manifest later must not invalidate the historical fact that Meta-OS correctly rejected deployment at that time.

## Authority boundary

The artifact always carries:

- `financial_authority = NONE`
- `payment_authority = NONE`
- `accounting_authority = NONE`
- `execution_authority = NONE`

A fresh outer SHA cannot convert `BLOCKED_BUILD_EVIDENCE` into `ADMITTED`: the verifier rebuilds the decision from the raw signed manifest, profile and source lock.

A future build-verified/deployable admission generation must be a new version rather than a reinterpretation of v1.
