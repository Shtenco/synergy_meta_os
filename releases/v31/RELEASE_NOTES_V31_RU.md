# SYNERGY META OS v31 Signed Durable Supervisor RC1

v31 закрывает следующий разрыв после v29 Full-RAM/HHDM: управляемый lifecycle
узлов больше не опирается на неподписанный JSON или на факт наличия артефакта.
Запуск требует двух независимых доказательств — подписанного manifest и
подписанного governance grant для **точного** digest/generation/service set.

## Реализовано

- canonical deterministic JSON;
- Ed25519 signed node manifest и отдельный signed activation grant;
- точный lock `turbo_linux` host commit + release SHA-256;
- capability registry и ceilings для типов сервисов;
- 64 service slots и строгий DAG;
- immutable SHA-256 CAS;
- SQLite `synchronous=FULL`, WAL, generation anti-rollback и nonce replay guard;
- атомарные `STAGED`/`ACTIVE`/`ROLLBACK` slots;
- два независимо проверяемых hash chains: state history и fsync audit log;
- transactional process replacement: неуспешный upgrade не останавливает старый;
- Linux compatibility sandbox: rlimits, `NO_NEW_PRIVS`, minimal env, no shell;
- CLI для offline manifest/evidence/status verification;
- CI и повторяемый qualification runner.

## Проверено 2026-08-30

- unit tests: 16/16 PASS;
- Ed25519 mutations: 10 000/10 000 rejected;
- CAS: 2 048/2 048 verified round-trips;
- durable activation: 1 000 cycles, 2 000 history entries, reopen PASS;
- audit: 512/512 fsync records verified;
- failed upgrade: 50/50 rejected, старый PID/manifest сохранены;
- native x86_64 QEMU full-RAM, 2 GiB, 4 CPU, VT-d/MSI-X: PASS;
- UEFI A/B/recovery: 6/6 PASS;
- host regressions + ASan/UBSan: PASS;
- architecture contract: 88 checks;
- requirements traceability: 54 requirements / 88 evidence links;
- kernel freeze: 43/43;
- W^X/minimality/security audit: PASS.

## Честная граница

Это **не Desktop Alpha и не production release**. Supervisor пока запускает
Linux compatibility services, а не является новым native TURBO service cell.
Физические NVMe/Ethernet/GPU/xHCI/HDA, TPM/Secure Boot production enrollment,
production keys, KASLR, масштабная persistent FS, native desktop apps,
AArch64 v31 и 8/24/72-hour/500-power-cut hardware gates остаются незакрытыми.

Любые финансовые, payment, accounting, treasury и blockchain-submission
полномочия в manifest/grant v31 равны `NONE`.

