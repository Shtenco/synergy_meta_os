# SYNERGY META OS v31 — Signed Durable Supervisor RC

v31 is the compatibility control plane above the existing TURBO META OS v29
native foundation.  It admits only canonical Ed25519-signed manifests, requires
a separate governance signature before activation, pins the exact host build,
and keeps activation state in a synchronous SQLite transaction plus an
independently verifiable hash chain.

This release candidate does **not** claim Desktop Alpha or production status.
The supervisor currently starts Linux compatibility services using rlimits and
`PR_SET_NO_NEW_PRIVS`; TURBO's native capability/process isolation remains the
host boundary.

## Authority flow

1. NEXUS may produce a bounded inference result.
2. AUTOPILOT may produce a proposal only.
3. Policy admits an exact signed node manifest.
4. A separate governance key signs an exact activation grant.
5. The supervisor starts only the granted service set and commits state only
   after every new process passes its health probe.

`ADMITTED`, `LAUNCHABLE`, `RUNNING`, and `PRODUCTION` are deliberately separate
states.  v31 never reports `PRODUCTION`.

## Security properties implemented

- deterministic JSON with floats and unsafe integers rejected;
- Ed25519 manifest and governance signatures with bounded validity windows;
- exact `turbo_linux` commit and release-SHA lock;
- fixed capability registry and per-service-kind capability ceilings;
- strict acyclic dependency graph, maximum 64 services;
- NEXUS and AUTOPILOT cannot receive financial execution authority;
- high-risk capabilities require hardware attestation;
- raw private-key bytes and `.key`/`.pem`/`.ppk` paths are rejected;
- immutable SHA-256 CAS with atomic publication and read-back verification;
- generation anti-rollback and activation nonce replay protection;
- transactional active/rollback/staged slots;
- append-only fsync audit chain and independent durable-state hash chain;
- failed upgrades preserve the old healthy process and active manifest.

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
PYTHONPATH=src python tools/qualify_v31.py \
  --output evidence/v31/QUALIFICATION.json
```

Useful offline inspection commands:

```bash
synergy-meta-os capability-registry-digest
synergy-meta-os verify-manifest MANIFEST.json --keys PUBLIC_KEYS.json
synergy-meta-os status --root NODE_ROOT
synergy-meta-os verify-evidence --root NODE_ROOT
```

Public-key files contain a JSON object of `key_id` to raw Ed25519 public-key
bytes encoded with Base64.  Private keys are intentionally not loaded by the
runtime CLI.

## Evidence

- `evidence/v31/STATUS.json` — claim ledger and honest gate state;
- `evidence/v31/QUALIFICATION.json` — repeatable stress results;
- `docs/REPOSITORY_REUSE_MATRIX_RU.md` — disposition of all 44 Shtenco repos;
- `releases/v31/RELEASE_NOTES_V31_RU.md` — Russian release notes.

The native v29 foundation remains a separate build tree.  Its x86_64 full-RAM
QEMU, VT-d/MSI-X, UEFI recovery, sanitizer, W^X and freeze gates were rerun for
this RC; their results are recorded in `STATUS.json` rather than represented as
new Python functionality.

