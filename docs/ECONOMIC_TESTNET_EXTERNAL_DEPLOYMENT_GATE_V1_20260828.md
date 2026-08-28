# Economic Testnet External Deployment Gate v1

This Meta-OS layer defines evidence requirements for a future persistent three-node Economic Testnet deployment. It does not create hosts or start services.

Gate root: `2d053095eac57dbf22e3fceaeec0aeadfa11577b42b7eb418f3661b18d20d40f`.

Pinned inputs are the Economic Testnet genesis `cfba3627...`, current testnet source `72a7853f...`, local persistence/restart evidence `7c533e6e...`, and Meta-OS Bootstrap v5 `6ccecccc...`.

Exactly three distinct node candidates are required. Each candidate must carry evidence digests for its HostProfile, SupervisorConfig, host fingerprint, artifact verification, persistent storage, restart recovery, deployment evidence/result, and transport endpoint. Node ids and host fingerprints must be unique. A cross-host checkpoint transcript digest is also required.

The canonical checked-in gate contains three null node slots and remains `BLOCKED_AWAITING_THREE_REAL_PERSISTENT_EXTERNAL_HOSTS`.

Even a structurally complete candidate reaches only `READY_FOR_EXTERNAL_DEPLOYMENT_EVIDENCE_VERIFICATION_NOT_EXECUTED`. It cannot self-assert a running testnet, consensus, finality, signing, blockchain submission, or financial/payment/accounting/execution authority. Independent evidence verification is a later step.
