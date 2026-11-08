#!/usr/bin/env python3
"""Q0.9 independent cohort pre-registration and full raw result validation."""
import sys,json,math,pathlib
from hq500m_oracle import expected,mix,N
base=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else "q09_cohort")
size=int(sys.argv[2]) if len(sys.argv)>2 else 12
assert 1<=size<=24
# Every candidate is selected *before* looking at learning outcomes:
# weak excitatory exact cross-region links from fixed 1024-neuron cortical module,
# ranked with SplitMix64 by (source globally-addressed ID, original gene slot).
candidates=[]
for source in range(1024*1024,1025*1024):
 for slot in range(24,32):
  dst,weight,gene,typ=expected(source,slot)
  w=weight/2500
  if weight>0 and 0.70<=w<0.74:
   rank=mix((source<<4)|(slot-24))
   candidates.append((rank,source,slot-24,dst,weight))
candidates.sort(key=lambda v:(v[0],v[1],v[2]))
cases=[]
complete=0
failure=0
for i in range(size):
 expected_rank,source,slot,dst,weight=candidates[i]
 data={}
 for mode in ("on","off","unpaired","cueonly"):
  p=base/f"trial{i:02d}_{mode}.json"
  if not p.exists():
   print(f"MISSING: {p}",file=sys.stderr)
   raise SystemExit(2)
  x=json.loads(p.read_text())
  assert x["format"]=="GENESIS-HQ500M-Q0.9-COHORT"
  assert x["protocol"]==mode and x["trial_id"]==i and x["candidate_pool_size"]==len(candidates)
  assert (x["cue_global_id"],x["gene_slot"]-24,x["readout_global_id"])==(source,slot,dst)
  assert abs(x["base_weight"]-weight/2500)<1e-5
  assert x["steps"]==240 and x["event_drops"]==0
  assert x["events_emitted"]==x["events_delivered"]+x["events_still_pending"]
  assert x["distractor_global_id"]==source+1 and x["distractor_readout_spikes"]==0
  assert x["pretraining_probe_cues"]==3 and x["posttraining_probe_cues"]==2
  assert x["retention_probe_cues"]==2 and x["paired_training_epochs"]==11
  assert x["learning_enabled"]==(mode!="off")
  if mode=="off":
   assert x["trained_synapse_delta"]==0 and x["learned_synapses_total"]==0
  data[mode]=x
 # Strict behavioral criterion, no posthoc omission.
 success=(data["on"]["pretraining_readout_spikes"]==0
  and data["on"]["posttraining_readout_spikes"]==2
  and data["on"]["retention_readout_spikes"]==2
  and all(data[m]["posttraining_readout_spikes"]==0 and data[m]["retention_readout_spikes"]==0
          for m in ("off","unpaired","cueonly"))
  and data["on"]["trained_synapse_delta"]>0)
 if success:complete+=1
 else:failure+=1
 cases.append({"trial_id":i,"source_global_id":source,"target_global_id":dst,
  "original_gene_slot":slot+24,"baseline_weight":weight/2500,
  "paired":{k:data["on"][k] for k in ("pretraining_readout_spikes","posttraining_readout_spikes","retention_readout_spikes","trained_synapse_delta")},
  "controls":{m:{"post":data[m]["posttraining_readout_spikes"],"retention":data[m]["retention_readout_spikes"]}
    for m in ("off","unpaired","cueonly")},"meets_criterion":success})
 print(f"TRIAL {i:02d}: {'PASS' if success else 'FAIL'}; baseline={data['on']['pretraining_readout_spikes']} "
       f"paired_post={data['on']['posttraining_readout_spikes']} paired_ret={data['on']['retention_readout_spikes']} "
       f"off={data['off']['retention_readout_spikes']} "
       f"unpaired={data['unpaired']['retention_readout_spikes']} "
       f"cueonly={data['cueonly']['retention_readout_spikes']}")
out={"format":"GENESIS-HQ500M-Q0.9-COHORT-REPORT","selection":"Deterministic splitmix64 rank of 137 baseline-weight-filtered excitatory C5 edges in one cortical 1024-neuron module; no selection by behavior",
     "candidate_pool":len(candidates),"cohort_size":size,"successes":complete,"failures":failure,
     "full_virtual_neurons":500_000_000,"actually_tested_pairs":size,
     "scoring":"zero baseline, 2/2 paired immediate and 2/2 paired delayed, 0/2 all 3 negative controls",
     "not_generalizable_to_human_brains":True,
     "cases":cases}
(base/"cohort_summary.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print("COHORT:",complete,"/",size,"passed, failures",failure)
