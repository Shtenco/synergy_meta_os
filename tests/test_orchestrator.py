import hashlib,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from runtime.orchestrator import ManifestError,NodeOrchestrator,verify_manifest

def manifest_for(root,attested=False):
    app=root/"svc.sh";app.write_text("#!/bin/sh\nexit 0\n");app.chmod(0o755)
    sha=hashlib.sha256(app.read_bytes()).hexdigest()
    return {"schema":1,"node_id":"dev-node","profile":"EDGE_CLIENT","attested":attested,"development":True,"generation":1,
            "services":[{"name":"edge","role":"EDGE_CLIENT","artifact":"svc.sh","sha256":sha,
                         "argv":["$ARTIFACT"],"capabilities":["network.connect","storage.read"],
                         "limits":{"memory_mib":32,"cpu_seconds":5,"open_files":64}}]}

def test_verify_stage_dryrun_and_rollback():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);m=manifest_for(root);p=root/"manifest.json";p.write_text(json.dumps(m))
        assert verify_manifest(p,root)["node_id"]=="dev-node"
        o=NodeOrchestrator(root,root/"state");o.stage(p);assert o.activate(dry_run=True)==[]
        rs=o.activate(dry_run=False)
        for r in rs:r.process.wait(timeout=2)
        m["generation"]=2;p.write_text(json.dumps(m));o.stage(p);o.activate(dry_run=True)

def test_capability_escalation_rejected():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);m=manifest_for(root);m["services"][0]["capabilities"].append("treasury.sign")
        p=root/"manifest.json";p.write_text(json.dumps(m))
        try:verify_manifest(p,root)
        except ManifestError:return
        raise AssertionError("authority escalation was accepted")
