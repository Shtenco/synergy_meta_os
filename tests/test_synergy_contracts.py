import json
from pathlib import Path

from runtime.synergy_contracts import CONTRACT_ID, node_manifest_payload


def test_node_manifest_contract_wraps_real_meta_os_manifest(tmp_path):
    artifact=tmp_path/"svc"
    artifact.write_bytes(b"hello")
    import hashlib
    manifest={
      "schema":1,
      "node_id":"node-dev",
      "profile":"EDGE_CLIENT",
      "attested":False,
      "development":True,
      "generation":1,
      "services":[{
        "name":"ui",
        "role":"EDGE_CLIENT",
        "artifact":"svc",
        "sha256":hashlib.sha256(b"hello").hexdigest(),
        "argv":["$ARTIFACT"],
        "capabilities":["storage.read","ui.present"],
        "limits":{"memory_mib":64,"cpu_seconds":10,"open_files":32}
      }]
    }
    path=tmp_path/"manifest.json"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    payload=node_manifest_payload(path,tmp_path)
    assert CONTRACT_ID=="synergy.runtime.node-manifest/v1"
    assert payload["node_id"]=="node-dev"
    assert payload["services"][0]["sha256"]==manifest["services"][0]["sha256"]
