# SYNERGY META-OS v30 Unified Node RC

This release combines the SYNERGY node orchestration/control plane with the TURBO Meta-OS v30 host bundle.

Authority remains split:

- `turbo_linux`: native kernel/host substrate, capability isolation, drivers, storage, network, MetaRAM/MetaFS.
- `synergy_meta_os`: signed-manifest-compatible node runtime, service lifecycle, role/capability policy, updates/rollback.

The host release is bound by exact hashes and is not reinterpreted as financial or blockchain authority.

## Runtime

`runtime/orchestrator.py` verifies exact artifact SHA-256, rejects role/capability escalation, requires attestation for high-value profiles, applies Linux compatibility resource limits, journals stage/activate/failure events, and maintains rollback manifests.

## Host v30 qualification

- sparse PMM: 128 GiB;
- canonical HHDM: `0xFFFF800000000000 + physical`;
- exactly 6 privileged service cells;
- 64 dynamic ELF64 application domains;
- MetaRAM ring-3 IPC pager: 3.258056 µs/page median average roundtrip, ~1198.951 MiB/s;
- MetaFS-X v0.3 four-snapshot result: 24,905,499 → 1,285,067 B = 19.3807× exact;
- SharedCAS / CIDv1 integration;
- full host regression, ASan/UBSan, security/architecture audit and UEFI A/B development bundle: PASS.

## Release boundary

This is an **OS RC / node runtime RC**, not a Desktop Alpha. Native x86_64 QEMU boot could not be re-run in the current build environment because QEMU/GRUB/xorriso are absent. Physical NVMe/Ethernet/GPU/xHCI/HDA, production TPM/Secure Boot/signing/KASLR and endurance gates remain `NOT_RUN`; AArch64 v30 rebuild is blocked by the absent cross toolchain.

The v23 network-plane archive was re-run as a regression base; its old static seventh supervisor is deliberately not part of the v30 authority graph.
