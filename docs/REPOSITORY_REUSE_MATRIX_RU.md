# Аудит всех репозиториев Shtenco для META OS v31

Дата аудита: 2026-08-30. Через GitHub API рекурсивно просмотрены default-branch
trees всех **44 из 44** доступных репозиториев, а также 29 веток
`synergy_meta_os` и четыре наиболее релевантные ветки `turbo_linux`.

Легенда решения:

- **ADAPTED** — контракт или ограниченный шаблон перенесён в v31 с новой
  реализацией и тестами;
- **PINNED** — компонент остаётся отдельным host/runtime и фиксируется по SHA;
- **FUTURE** — полезен следующему слою, но не включён в доверенный v31 runtime;
- **DOMAIN** — прикладной пакет; не получает системных полномочий;
- **NO-RUNTIME** — сайт, placeholder или материал без исполняемого вклада.

| № | Репозиторий | Найденная роль | Решение v31 |
|---:|---|---|---|
| 1 | `synergy_meta_os` | signed manifest, admission, artifact/state lifecycle, AUTOPILOT gates | **ADAPTED**: canonical manifest, отдельный activation grant, CAS, generation/nonce guards |
| 2 | `turbo_linux` | нативный x86/AArch64 substrate, HHDM, MetaRAM/MetaFS experiments | **PINNED**: commit `81fa56e…`, release SHA `f2aa342…`; код host не дублируется |
| 3 | `synergy_system` | constitution и federation/authority boundaries | **ADAPTED**: authority всегда явная и не выводится из admission |
| 4 | `synergynet` | транспорт узла | **FUTURE**: network capabilities ограничены, физический transport не заявлен |
| 5 | `agi_nexus` | proof-first bounded inference | **ADAPTED**: `NEXUS` только inference/read/telemetry |
| 6 | `agi_autopilot` | proposal/control plane | **ADAPTED**: AUTOPILOT proposal-only, без execution authority |
| 7 | `ai_language` | semantic trace и EML contracts | **ADAPTED**: детерминированные подписываемые байты и явные статусы |
| 8 | `agi_olga` | collective protocol и ledger patterns | **ADAPTED**: hash-chained audit/state evidence |
| 9 | `blochain_budget` | append-only/Merkle provenance | **ADAPTED**: append-only SHA-256 chains; финансовые функции не перенесены |
| 10 | `ai_compress` | content compression | **FUTURE**: только content-cache слой; не считается RAM/диском |
| 11 | `qr_compress` | QR/content packaging | **FUTURE**: пользовательский codec, не TCB |
| 12 | `motherboard_xpu_xml` | EML/XPU ISA и device-profile material | **FUTURE**: input для device manifest, не готовый native driver |
| 13 | `synergy_metachain` | metachain placeholder | **FUTURE**: до появления проверяемого protocol/runtime |
| 14 | `synergy_ai_blockchain` | AI/blockchain placeholder | **FUTURE**: никакой implicit consensus authority |
| 15 | `synergychain` | Solidity chain contracts | **DOMAIN**: blockchain submission authority по умолчанию `NONE` |
| 16 | `usds` | Solidity stable-asset contracts | **DOMAIN**: treasury/signing выключены; ключевые файлы не читались и не копировались |
| 17 | `synergy_pay_system` | payment manifests/readiness/provider patterns | **DOMAIN**: полезны provider URI; платежные полномочия `NONE` |
| 18 | `synergy_financial_os` | financial OS placeholder | **DOMAIN**: не включён в v31 |
| 19 | `ai_financial_system` | финансовая аналитика | **DOMAIN**: read/proposal only до отдельного hardware-attested grant |
| 20 | `cashero` | прикладной finance/payment проект | **DOMAIN**: изолирован от supervisor authority |
| 21 | `midas_ai` | AI/quant приложение | **DOMAIN**: кандидат на app domain |
| 22 | `midas_ai_trading_system` | trading runtime | **DOMAIN**: внешние сделки не разрешены v31 |
| 23 | `midas_lite` | облегчённый trading runtime | **DOMAIN**: кандидат на совместимый app domain |
| 24 | `ai_trade_terminal` | торговый terminal | **DOMAIN**: UI/read-only до отдельной авторизации |
| 25 | `algotrading_graph_system` | пустой/неразвёрнутый graph project | **NO-RUNTIME** |
| 26 | `multi_threaded_trading_robot_with_machine_learning_python` | Python/MT5 robot | **DOMAIN**: не TCB, не автозапускается |
| 27 | `global_liquidity_dataminer` | macro data miner | **DOMAIN**: read/analytics candidate |
| 28 | `swap_arbitrage_metatrader_5` | swap-arbitrage research | **DOMAIN** |
| 29 | `computer_vision_trading_metatrader_5` | vision trading research | **DOMAIN** |
| 30 | `cross_forex_arbitrage_trading_metatrader_5` | cross-FX research | **DOMAIN** |
| 31 | `quantum-trading_metatrader5` | IBM-Q trading research | **DOMAIN** |
| 32 | `3D_bars_market_structure` | market visualization/research | **DOMAIN** |
| 33 | `binary_quantum_theory` | большой Python research corpus | **DOMAIN**: future NEXUS workload, не kernel/runtime |
| 34 | `cold_nuclear` | scientific research | **DOMAIN**: future NEXUS workload |
| 35 | `nexus_science_agent` | science-agent placeholder | **DOMAIN**: требует bounded inference contract |
| 36 | `ai_coder` | минимальный/placeholder coder project | **NO-RUNTIME** |
| 37 | `synergy_app` | Python application | **DOMAIN**: app package candidate |
| 38 | `sinergy_app` | placeholder application | **NO-RUNTIME** до появления содержимого |
| 39 | `sinergy-super-app` | HTML super-app | **DOMAIN**: future desktop/web surface |
| 40 | `synergy_eurasian` | public placeholder | **NO-RUNTIME** |
| 41 | `synergy_matrix_sota` | public placeholder | **NO-RUNTIME** |
| 42 | `synergychain.github.io` | public website | **NO-RUNTIME** |
| 43 | `shtenco.github.io` | статическая страница | **NO-RUNTIME** |
| 44 | `shtencoauantai.github.io` | статическая страница | **NO-RUNTIME** |

Фактическая инвентаризация — 44 уникальных имени, приведённых ниже:

```text
3D_bars_market_structure, agi_autopilot, agi_nexus, agi_olga,
ai_coder, ai_compress, ai_financial_system, ai_language, ai_trade_terminal,
algotrading_graph_system, binary_quantum_theory, blochain_budget, cashero,
cold_nuclear, computer_vision_trading_metatrader_5,
cross_forex_arbitrage_trading_metatrader_5, global_liquidity_dataminer,
midas_ai, midas_ai_trading_system, midas_lite, motherboard_xpu_xml,
multi_threaded_trading_robot_with_machine_learning_python,
nexus_science_agent, qr_compress, quantum-trading_metatrader5,
shtenco.github.io, shtencoauantai.github.io, sinergy-super-app, sinergy_app,
swap_arbitrage_metatrader_5, synergy_ai_blockchain, synergy_app,
synergy_eurasian, synergy_financial_os, synergy_matrix_sota,
synergy_meta_os, synergy_metachain, synergy_pay_system, synergy_system,
synergychain, synergychain.github.io, synergynet, turbo_linux, usds
```

## Что сознательно не перенесено

- приватные ключи, credential-файлы и любые их значения;
- trading/payment/treasury authority;
- заявления о «виртуальной памяти» из compression ratios;
- статический седьмой privileged process;
- host-only MetaRAM/MetaFS модели как доказательство native persistent FS;
- placeholder-код без тестируемого контракта.

Итоговый invariant v31: **ровно существующий native host boundary плюс
непривилегированный совместимый supervisor; NEXUS → proposal → policy →
governance grant → bounded activation**.
