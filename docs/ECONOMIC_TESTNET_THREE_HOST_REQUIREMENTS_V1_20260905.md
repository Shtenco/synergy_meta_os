# Economic Testnet — Three External Hosts Requirements v1

Status: `BLOCKED_AWAITING_THREE_REAL_PERSISTENT_EXTERNAL_HOSTS_AND_SAFE_ACCESS`

This document is the operator-facing companion to the existing Economic Testnet External Deployment Gate v1. It does not create hosts and does not claim an external testnet is running.

## Required physical resources

Exactly three distinct persistent external hosts are required. The following do not count as three hosts: three containers on one server, three localhost processes, synthetic GitHub Actions runners, or transient processes without durable state.

Each host must provide evidence for:

- HostProfile;
- SupervisorConfig;
- unique host fingerprint;
- exact artifact/source identity verification;
- persistent durable state;
- fresh process restart/recovery;
- deployment evidence and deployment result;
- non-loopback transport endpoint.

The three hosts must also produce a cross-host checkpoint propagation transcript with an independently digestible artifact identity.

## Recommended initial profile — non-binding

A first engineering deployment can start small, for example approximately 1–2 vCPU, 2 GB RAM and 20–30 GB SSD per node on Ubuntu 24.04 LTS or another controlled compatible Linux environment. These numbers are operational recommendations only; they are not part of the formal gate.

Using different providers or regions is preferred because it increases failure-domain independence, but the formal requirement is distinct persistent external hosts with unique fingerprints and non-loopback connectivity.

## Safe execution access

Accepted pattern: an operator-controlled VPS/cloud connector or an operator-run bootstrap command that returns evidence/log artifacts.

Forbidden pattern: transmitting SSH private keys, seed phrases, wallet private keys, API secrets or raw signing material through chat or committing them to Git.

The 2026-09-04 TURBO Linux committed SSH-key incident is an explicit reason for this fail-closed rule. Any key previously committed must be treated as compromised until externally rotated/revoked; deleting it from a branch is not sufficient.

## Required deployment/recovery test sequence

1. deploy all three nodes and verify unique host identity;
2. verify exact source/artifact identity on every host;
3. establish non-loopback cross-host transport;
4. propagate checkpoint C1 across all hosts;
5. propagate and persist C2;
6. stop all node processes;
7. restart each node as a fresh process and recover persisted C2;
8. deliberately lag one node and verify catch-up;
9. propagate C3 and verify identical terminal checkpoint on all hosts;
10. restart again and verify C3 recovery;
11. replay an old checkpoint and require rejection;
12. tamper with persisted state in a controlled test and require fail-closed detection;
13. generate host-specific evidence roots and one cross-host transcript root.

## Authority boundary

A successful three-host deployment proves external-host deployment/recovery evidence only. It does not automatically prove consensus safety, finality, production readiness, financial/payment/accounting authority, signing authority or permission to submit transactions to any public blockchain.

All production promotion and canonical merge decisions remain human-maintainer/governance actions.

## Done condition

The physical blocker is removed only when three distinct host candidates replace the current null slots and all required evidence artifacts are independently verifiable. A later evidence generation may then change the gate to a readiness status; the requirements document itself cannot self-promote the testnet to running or production.
