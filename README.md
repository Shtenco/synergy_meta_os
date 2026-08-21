# SYNERGY META-OS

**Runtime orchestration layer for a complete SYNERGY node.**

Architecture root: `Shtenco/synergy_system`  
Target host substrate: `Shtenco/turbo_linux`  
P2P transport: `Shtenco/synergynet`

## Role

`synergy_meta_os` is the **running service orchestrator** of an actual node.

Do not confuse it with `synergy_system`:

```text
synergy_system   = architecture, federation, authority map
synergy_meta_os  = runtime supervisor of services on one node
```

## Target node architecture

```text
Signed Node Manifest
        ↓
Host Attestation / Node Identity
        ↓
Capability & Service Graph
        ↓
┌──────────────────────────────────────────────┐
│ SYNERGY Meta-OS                              │
│                                              │
│ SynergyNet daemon                            │
│ Blockchain node role (if authorized)         │
│ MetaPay service role (if authorized)         │
│ Financial OS service role (if authorized)    │
│ NEXUS inference / agents                     │
│ Business Autopilot services                  │
│ Compression/content cache                    │
│ Storage / update / rollback                  │
│ Audit / telemetry / health                   │
└──────────────────┬───────────────────────────┘
                   ↓
          TURBO Linux / compatible host
```

## Non-negotiable authority rule

Meta-OS orchestrates authorities; it does **not merge them**.

A root/supervisor process must not be able to turn:

```text
network privilege → treasury privilege
AI privilege      → payment privilege
blockchain role   → accounting authority
UI role           → ledger mutation
```

Service capabilities should be explicit, revocable and least-privilege.

## Target modules

```text
synergy_meta_os/
  manifest/
  identity/
  attestation/
  capabilities/
  service_graph/
  lifecycle/
  scheduler/
  network/
  blockchain/
  finance/
  agents/
  storage/
  updates/
  rollback/
  observability/
  audit/
```

## Signed node manifest

A node manifest should describe, at minimum:

- node identity/profile;
- software artifact hashes;
- enabled service roles;
- capability grants;
- required ports/endpoints;
- resource limits;
- data directories;
- key references (never raw keys);
- upgrade/rollback policy;
- minimum compatible schema generations;
- expected health checks;
- trust roots / signing policy.

## Node role profiles

Not every node runs everything.

Examples:

```text
EDGE_CLIENT
P2P_RELAY
CONTENT_CACHE
NEXUS_COMPUTE
BLOCKCHAIN_PEER
BLOCKCHAIN_VALIDATOR
METAPAY_GATEWAY
FINANCIAL_SERVICE
BUSINESS_AUTOPILOT
FULL_SYNERGY_NODE
```

High-value roles must require explicit authorization/attestation and must not be inferred from installed software.

## TURBO Linux integration

The preferred long-term host is `turbo_linux`, especially for:

- capability-oriented service isolation;
- bounded IPC;
- protected secrets;
- VM/compatibility domains;
- secure update/rollback;
- device and network service separation.

Meta-OS must also support a compatibility profile on conventional Linux during development.

## SynergyNet integration

SynergyNet is the data-plane transport. Meta-OS controls lifecycle/resource policy around the daemon but does not redefine its routing protocol.

## Financial integration

Meta-OS may launch Financial OS / MetaPay components only on authorized nodes.

It must never interpret “service is running” as “financial action is authorized”.

## Update model

Target update flow:

```text
new signed manifest
→ artifact hash verification
→ compatibility check
→ staged service update
→ health/evidence gates
→ activate
→ automatic rollback on failure
```

Financial and blockchain service updates should bind exact source/build artifacts and require stronger governance than ordinary UI updates.

## Initial milestone

The first meaningful Meta-OS milestone is one reproducible local node that can:

1. verify a signed development manifest;
2. launch isolated SynergyNet + NEXUS + read-only control-plane services;
3. enforce declared capability/resource boundaries;
4. collect deterministic service/audit evidence;
5. update one service and rollback safely;
6. prove that disabled financial/blockchain roles cannot be activated by an unprivileged service.

## Principle

**Meta-OS is the conductor of the node, not the owner of every instrument.**
