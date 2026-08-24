# AUTOPILOT V5 AI Node Production Bootstrap v5

Root: `6ccecccc03189c6de934abf146cab87bb25b022551ba8d453cfefd4f5a3cdffd`.

This is the current operator-facing production bootstrap contract after Pre-Production RC5 full-domain closure. It does not launch the node and cannot grant itself startup authority.

Pinned current roots include RC5 `0dd56320…`, DeploymentReference v2 `87b9bb81…`, AI Blockchain Commitment v3 `608b0ca9…`, Registry v3, Meta-OS Profile/Admission v3, SynergyNet LocationEvidence v3 and TransportBinding v2, plus exact NEXUS and SynergyNet artifact identities.

Exactly seven fresh production roots remain required:
1. persistent production HostProfile;
2. production SupervisorConfig;
3. fresh on-host artifact verification;
4. fresh health and transport roundtrip evidence;
5. production DeploymentEvidence;
6. production DeploymentResult;
7. explicit governance promotion evidence.

Historical LAB Host/Supervisor/Deployment roots are forbidden as production inputs. Default state is blocked. Even with all seven fresh roots supplied, the evaluator returns only `READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED`; startup remains false until a separate authorized production execution generation exists.
