# META-OS — capability-bound node orchestration

## Implemented engineering achievement

The project has a real Linux-compatible orchestrator in [runtime/orchestrator.py](../runtime/orchestrator.py). It models a signed-artifact-oriented service supervisor rather than merely a topology diagram. Service manifests specify node ID, profile, attestation flag, exact executable artifact digest, command-line vector, authorized capabilities and CPU/memory/file-descriptor limits. Validation rejects undeclared fields, unknown roles, escaped paths and SHA-256 mismatches.

The design's key original principle is **authority separation across co-located services**. Running a network relay does not grant ledger rights; running an AI model does not confer treasury signing rights. The role ceiling maps each service role to a bounded subset of capabilities, while dangerous operations require explicit attestation.

## Formal safety policy

For a service s with role r, the permission invariant is

$$
\mathrm{Caps}(s)\subseteq\mathrm{Ceiling}(r).
$$

Before launching an artifact a, the supervisor verifies

$$
\operatorname{SHA256}(\operatorname{bytes}(a))=\mathrm{ManifestDigest}(a).
$$

These checks bind a process to declared source bytes and capabilities, not to verified correctness of its algorithms.

## Lifecycle and research agenda

The implementation includes staged manifest files, JSONL audit records, activation state, rollback snapshots and Linux resource limits. It is useful for experimental edge devices, composable AI nodes and regulated financial service separation.

A rigorous next phase will run adversarial manifests: forbidden role escalation, wrong digest, symlink path escape, failed activation, process crash and attempted financial capability from a read-only node. Publish deterministic receipts for each denied action and compare restart/recovery under fault injection. The strongest research target is a **reproducible capability-governed node**, not a claim of a completed new operating-system kernel.

## Position within SYNERGY

SYNERGY SYSTEM maintains the federation's authority registry; Meta-OS runs declared services; TURBO Core is a candidate low-level substrate; SynergyNet handles data delivery. These responsibilities should remain separate even when deployed on one machine.

[Orchestrator](../runtime/orchestrator.py) · [Example manifest](../manifest/example.dev.json) · [Tests](../tests/test_orchestrator.py)
