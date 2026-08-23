from __future__ import annotations
import json, signal, sys, time
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(ROOT/'src'))
from synergy_autopilot_v5_node import KnowledgePlane,TrainedRouter,SynergyAutopilotV5NodeKernel,CapabilityPolicy,SMMNode,NexusBridge
stop=False
def h(*_):
 global stop; stop=True
signal.signal(signal.SIGTERM,h); signal.signal(signal.SIGINT,h)
k=KnowledgePlane.load(ROOT/'knowledge'/'corpus.jsonl')
r=TrainedRouter.load(ROOT/'knowledge'/'router_model.json')
p=CapabilityPolicy(allow_external_side_effects=False,allow_blockchain_commit=False)
n=NexusBridge(str(ROOT/'artifacts'/'nexus'/'nexus_e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325.pyz'))
node=SynergyAutopilotV5NodeKernel(k,r,policy=p,nexus=n,smm=SMMNode(p))
status={'schema':'synergy.autopilot-v5-ai-node-resident-status/v1','status':'READY','node_id':'synergy-autopilot-v5-ai-node','nexus_status':node.nexus.status()['payload']['status'],'knowledge_digest':node.knowledge.digest,'router_model_digest':node.router.model_digest or node.router.to_dict()['model_digest'],'external_side_effects':'DISABLED_BY_DEFAULT','financial_authority':'NONE','payment_authority':'NONE','accounting_authority':'NONE','execution_authority':'NONE'}
print(json.dumps(status,sort_keys=True),flush=True)
while not stop: time.sleep(0.2)
print(json.dumps({'schema':'synergy.autopilot-v5-ai-node-resident-stop/v1','status':'STOPPED_GRACEFULLY','execution_authority':'NONE'},sort_keys=True),flush=True)
