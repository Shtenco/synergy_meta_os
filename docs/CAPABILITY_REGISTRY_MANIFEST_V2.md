# Capability-registry-backed node manifest v2

`synergy.node-manifest/v2` preserves the signed-manifest model while removing the future hard-coded capability/service taxonomy from Meta-OS.

The manifest pins an exact `synergy.capability-registry/v1` digest. Capabilities and service kinds are validated from those registry bytes. Service repository identity must exactly match the owner registered for its kind, and required capabilities must exactly match the registry contract.

This generation enables future roles such as `SCIENCE_RESEARCH`/`SCIENCE_AGENT` and `MIDAS_ANALYSIS`/`MIDAS` without editing historical manifest v1.

A capability remains an operational-role declaration only. It grants no accounting, payment, settlement, trading execution, scientific-truth or architecture authority. A valid signed v2 manifest still has `execution_authority=NONE` and does not start a process by itself.

Registry generation changes require new immutable registry bytes; manifest v2 pins the generation it was evaluated against.
