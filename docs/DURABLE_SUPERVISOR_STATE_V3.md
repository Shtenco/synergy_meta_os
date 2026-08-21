# Durable Supervisor State v3

V3 makes Meta-OS supervisor state restart-persistent before any process-execution adapter is introduced.

## State chain

Each `synergy.supervisor-state/v3` records:

- node identity;
- accepted manifest generation;
- exact manifest body digest;
- current STOPPED/RUNNING service states and running artifact digest;
- previous state digest;
- `execution_authority=NONE`;
- content digest over canonical JSON bytes.

The durable store keeps immutable history files keyed by state digest and atomically advances a small current-pointer file.

## Safety invariants

- generation rollback is rejected after restart;
- the same generation cannot silently change manifest bytes;
- stale writers cannot fork the current chain;
- history and pointer bytes are reverified when read;
- a running service cannot exist without an artifact digest;
- persisted state still has no authority to spawn/kill processes.

## Deliberate boundary

This generation is not a distributed consensus store and is not a production process manager. A future process adapter must consume an already-verified lifecycle action and update durable state only after independently observed process outcomes. Systemd/container integration, crash recovery and OS sandboxing are separate generations.
