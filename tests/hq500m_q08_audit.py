#!/usr/bin/env python3
"""Independent GENESIS Q0.8 controlled associative-learning assay verifier."""
import sys,json,pathlib,math
from hq500m_oracle import expected,N
def load(path):
 x=json.loads(pathlib.Path(path).read_text())
 assert x["format"]=="GENESIS-HQ500M-Q0.8-ASSOCIATION"
 assert x["virtual_neurons"]==N and x["gpu_count"]==8
 src=x["cue_global_id"];dst=x["readout_global_id"];slot=x["gene_slot"]
 assert 0<=src<N and 0<=dst<N and 24<=slot<=31
 e=expected(src,slot)
 assert e[0]==dst and e[1]>0 and e[2]==1
 assert abs(e[1]/2500-x["base_weight"])<1e-6
 assert abs(x["final_effective_synaptic_weight"]-x["base_weight"]*(1+x["trained_synapse_delta"]))<2e-5
 assert x["pretraining_probe_cues"]==3 and x["posttraining_probe_cues"]==2
 assert x["retention_probe_cues"]==2 and x["steps"]==240
 assert x["paired_training_epochs"]==11
 assert x["pretraining_readout_spikes"]>=0
 assert x["event_drops"]==0
 assert x["events_emitted"]==x["events_delivered"]+x["events_still_pending"]
 assert x["distractor_global_id"]==src+1
 assert len(x["spikes_by_gpu"])==8
 for t in x["readout_spike_steps"]:assert 0<=t<x["steps"]
 print(json.dumps({"status":"PASS","protocol":x["protocol"],"pre":x["pretraining_readout_spikes"],
  "post":x["posttraining_readout_spikes"],"distractor":x["distractor_readout_spikes"],"retention":x["retention_readout_spikes"],
  "final_gain":x["final_effective_synaptic_weight"],"learning":x["learning_enabled"]}))
 return x
def compare(path1,path2):
 a=load(path1);b=load(path2)
 keys=[k for k in a if k!="runtime_seconds"]
 assert all(a[k]==b[k] for k in keys),"resume altered assay metrics"
 print(json.dumps({"resume":"PASS","equal_fields":len(keys)}))
if __name__=="__main__":
 if len(sys.argv)!=6:raise SystemExit("Usage: audit learn off unpaired cueonly resumed")
 a=load(sys.argv[1]);b=load(sys.argv[2]);c=load(sys.argv[3]);d=load(sys.argv[4])
 assert [x["protocol"] for x in (a,b,c,d)]==["on","off","unpaired","cueonly"]
 assert len({(x["cue_global_id"],x["readout_global_id"],x["gene_slot"]) for x in (a,b,c,d)})==1
 assert all(x["pretraining_readout_spikes"]==0 for x in (a,b,c,d))
 assert a["posttraining_readout_spikes"]==2
 assert a["retention_readout_spikes"]==2
 assert all(x["posttraining_readout_spikes"]==0 and x["retention_readout_spikes"]==0 for x in (b,c,d))
 assert all(x["distractor_readout_spikes"]==0 for x in (a,b,c,d))
 assert a["trained_synapse_delta"]>0.0
 assert b["learned_synapses_total"]==0
 assert c["trained_synapse_delta"]<0.05
 assert d["trained_synapse_delta"]==0
 compare(sys.argv[1],sys.argv[5])
 print("GENESIS Q0.8 controlled associative acquisition + negative controls + checkpoint replay: PASS")
