#!/usr/bin/env python3
"""SYNERGY Meta-OS node orchestrator v30 compatibility runtime.

Security model:
- manifest declares roles, artifacts and capabilities;
- artifact SHA-256 is verified before launch;
- high-value roles require explicit attestation;
- services cannot infer treasury/ledger authority from network/AI/UI capabilities;
- update is staged and journaled; activation is explicit; rollback is deterministic.

This compatibility runtime targets conventional Linux during development. The native
TURBO host uses the same manifest/capability semantics around ring-3 service cells.
"""
from __future__ import annotations

import argparse, hashlib, json, os, resource, subprocess, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = 1
KNOWN_ROLES = {
    "EDGE_CLIENT", "P2P_RELAY", "CONTENT_CACHE", "NEXUS_COMPUTE",
    "BLOCKCHAIN_PEER", "BLOCKCHAIN_VALIDATOR", "METAPAY_GATEWAY",
    "FINANCIAL_SERVICE", "BUSINESS_AUTOPILOT", "FULL_SYNERGY_NODE",
}
HIGH_VALUE_ROLES = {"BLOCKCHAIN_VALIDATOR", "METAPAY_GATEWAY", "FINANCIAL_SERVICE", "FULL_SYNERGY_NODE"}
KNOWN_CAPS = {
    "network.connect", "network.listen", "storage.read", "storage.write",
    "content.cache", "nexus.infer", "agents.execute", "observability.emit",
    "update.stage", "update.activate", "blockchain.read", "blockchain.peer",
    "blockchain.validate", "finance.read", "finance.execute", "treasury.sign",
    "ui.present",
}
DANGEROUS_CAPS = {"blockchain.validate", "finance.execute", "treasury.sign", "update.activate"}
ROLE_CAP_CEILING = {
    "EDGE_CLIENT": {"network.connect", "storage.read", "observability.emit", "ui.present"},
    "P2P_RELAY": {"network.connect", "network.listen", "storage.read", "storage.write", "observability.emit"},
    "CONTENT_CACHE": {"network.connect", "network.listen", "storage.read", "storage.write", "content.cache", "observability.emit"},
    "NEXUS_COMPUTE": {"network.connect", "storage.read", "nexus.infer", "observability.emit"},
    "BLOCKCHAIN_PEER": {"network.connect", "network.listen", "storage.read", "storage.write", "blockchain.read", "blockchain.peer", "observability.emit"},
    "BLOCKCHAIN_VALIDATOR": {"network.connect", "network.listen", "storage.read", "storage.write", "blockchain.read", "blockchain.peer", "blockchain.validate", "observability.emit"},
    "METAPAY_GATEWAY": {"network.connect", "network.listen", "storage.read", "storage.write", "finance.read", "finance.execute", "observability.emit"},
    "FINANCIAL_SERVICE": {"network.connect", "storage.read", "storage.write", "finance.read", "finance.execute", "treasury.sign", "observability.emit"},
    "BUSINESS_AUTOPILOT": {"network.connect", "storage.read", "storage.write", "nexus.infer", "agents.execute", "observability.emit"},
    "FULL_SYNERGY_NODE": KNOWN_CAPS - {"treasury.sign"},
}

class ManifestError(ValueError): pass

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def load_manifest(path: Path) -> dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    required={"schema","node_id","profile","attested","development","services"}
    if set(obj) - (required|{"generation","signature_policy","metadata"}):
        raise ManifestError("unknown top-level manifest fields")
    if not required <= set(obj): raise ManifestError("missing required manifest fields")
    if obj["schema"] != SCHEMA: raise ManifestError("unsupported schema")
    if obj["profile"] not in KNOWN_ROLES: raise ManifestError("unknown node profile")
    if not isinstance(obj["services"],list) or len(obj["services"])>64: raise ManifestError("services must be list <=64")
    if obj["profile"] in HIGH_VALUE_ROLES and not obj["attested"]: raise ManifestError("high-value profile requires attestation")
    return obj

def verify_service(service: dict[str,Any], root: Path, node: dict[str,Any]) -> None:
    required={"name","role","artifact","sha256","argv","capabilities","limits"}
    if set(service)!=required: raise ManifestError(f"service {service.get('name','?')}: exact fields required")
    role=service["role"]
    if role not in KNOWN_ROLES: raise ManifestError("unknown service role")
    caps=set(service["capabilities"])
    if not caps <= KNOWN_CAPS: raise ManifestError(f"{service['name']}: unknown capability")
    if not caps <= ROLE_CAP_CEILING[role]: raise ManifestError(f"{service['name']}: role capability escalation")
    if caps & DANGEROUS_CAPS and not node["attested"]: raise ManifestError(f"{service['name']}: dangerous capability requires attestation")
    artifact=(root/service["artifact"]).resolve()
    if root.resolve() not in artifact.parents and artifact != root.resolve(): raise ManifestError("artifact escapes root")
    if not artifact.is_file(): raise ManifestError(f"artifact missing: {artifact}")
    if sha256_file(artifact) != service["sha256"].lower(): raise ManifestError(f"artifact hash mismatch: {service['name']}")
    lim=service["limits"]
    if set(lim)!={"memory_mib","cpu_seconds","open_files"}: raise ManifestError("exact limits required")
    if not (16 <= int(lim["memory_mib"]) <= 65536): raise ManifestError("memory limit")
    if not (1 <= int(lim["cpu_seconds"]) <= 86400): raise ManifestError("cpu limit")
    if not (16 <= int(lim["open_files"]) <= 65536): raise ManifestError("open-files limit")
    if not isinstance(service["argv"],list) or not service["argv"]: raise ManifestError("argv")

def verify_manifest(manifest_path: Path, root: Path) -> dict[str,Any]:
    obj=load_manifest(manifest_path)
    for s in obj["services"]: verify_service(s,root,obj)
    return obj

def _limits(lim: dict[str,int]):
    def apply():
        mem=int(lim["memory_mib"])*1024*1024
        resource.setrlimit(resource.RLIMIT_AS,(mem,mem))
        cpu=int(lim["cpu_seconds"]);resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu))
        nofile=int(lim["open_files"]);resource.setrlimit(resource.RLIMIT_NOFILE,(nofile,nofile))
        os.setsid()
    return apply

@dataclass
class RunningService:
    name:str
    process:subprocess.Popen

class NodeOrchestrator:
    def __init__(self, root: Path, state_dir: Path):
        self.root=root.resolve();self.state_dir=state_dir.resolve();self.state_dir.mkdir(parents=True,exist_ok=True)
        self.running:list[RunningService]=[]
    def journal(self,event:str,**data):
        rec={"ts_ns":time.time_ns(),"event":event,**data}
        with (self.state_dir/"audit.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(rec,sort_keys=True)+"\n")
    def stage(self,manifest_path:Path)->dict[str,Any]:
        obj=verify_manifest(manifest_path,self.root)
        staged=self.state_dir/"staged_manifest.json"
        staged.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding="utf-8")
        self.journal("manifest_staged",generation=obj.get("generation",0),services=len(obj["services"]))
        return obj
    def activate(self,dry_run:bool=False):
        staged=self.state_dir/"staged_manifest.json"
        if not staged.exists(): raise ManifestError("nothing staged")
        obj=verify_manifest(staged,self.root)
        old=self.state_dir/"active_manifest.json"
        if old.exists(): (self.state_dir/"rollback_manifest.json").write_bytes(old.read_bytes())
        if dry_run:
            self.journal("activation_dry_run",services=len(obj["services"]));return []
        launched=[]
        try:
            for s in obj["services"]:
                artifact=(self.root/s["artifact"]).resolve()
                argv=[str(artifact) if x=="$ARTIFACT" else str(x) for x in s["argv"]]
                env={"PATH":"/usr/bin:/bin","SYNERGY_SERVICE":s["name"],"SYNERGY_CAPABILITIES":",".join(s["capabilities"])}
                p=subprocess.Popen(argv,cwd=self.root,env=env,stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   preexec_fn=_limits(s["limits"]),text=False)
                launched.append(RunningService(s["name"],p));self.journal("service_started",name=s["name"],pid=p.pid)
            old.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding="utf-8")
            self.running.extend(launched);self.journal("manifest_activated",services=len(launched));return launched
        except Exception:
            for r in launched:
                try:r.process.terminate()
                except Exception:pass
            self.journal("activation_failed",started=len(launched));raise
    def rollback(self):
        rb=self.state_dir/"rollback_manifest.json"
        if not rb.exists():raise ManifestError("rollback manifest absent")
        (self.state_dir/"staged_manifest.json").write_bytes(rb.read_bytes())
        self.journal("rollback_staged")

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--state",default=".synergy-state")
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("verify");p.add_argument("manifest")
    p=sub.add_parser("stage");p.add_argument("manifest")
    p=sub.add_parser("activate");p.add_argument("--dry-run",action="store_true")
    sub.add_parser("rollback")
    a=ap.parse_args(argv);root=Path(a.root);o=NodeOrchestrator(root,Path(a.state))
    if a.cmd=="verify": print(json.dumps(verify_manifest(Path(a.manifest),root),indent=2));return 0
    if a.cmd=="stage": o.stage(Path(a.manifest));print("STAGED");return 0
    if a.cmd=="activate": o.activate(a.dry_run);print("ACTIVATED" if not a.dry_run else "DRY_RUN_PASS");return 0
    o.rollback();print("ROLLBACK_STAGED");return 0

if __name__=="__main__": raise SystemExit(main())
