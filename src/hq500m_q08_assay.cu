// Q0.8: associative cue/readout assay using exact HQ500M global C5 synapse.
// This is a small controlled experimental circuit, not human cognition.
#define main genesis_q08_main
#include "genesis_hq500m_q08.cu"
#undef main
#include <sstream>
static int cue_at(int tick,bool train_cue){
 if(tick==4||tick==10||tick==16||tick==158||tick==178||tick==210||tick==230)return 1;
 if(train_cue)for(int k=0;k<11;k++)if(tick==30+10*k)return 1;
 return 0;
}
static int teacher_at(int tick){
 for(int k=0;k<11;k++)if(tick==31+10*k)return 1;
 return 0;
}
static int readout(const Scheduler &s,int tick){
 if(tick<0||tick>=(int)s.watched_spikes_by_step.size())return 0;
 return s.watched_spikes_by_step[tick];
}
static int sum_probe(const Scheduler&s,const std::vector<int>&probe){
 int n=0;for(int t:probe)n+=readout(s,t+1);
 return n;
}
int main(int argc,char**argv){
 if(argc<4){
  fprintf(stderr,"Usage: %s on|off|unpaired|cueonly total_steps output.json [checkpoint] [--resume]\n",argv[0]);
  return 2;
 }
 std::string protocol=argv[1];
 if(protocol!="on"&&protocol!="off"&&protocol!="unpaired"&&protocol!="cueonly")
  throw std::runtime_error("learning protocol must be on|off|unpaired|cueonly");
 bool learn=protocol!="off",train_cue=protocol!="unpaired",teacher_enabled=protocol!="cueonly";
 int steps=atoi(argv[2]);if(steps<8||steps>240)throw std::runtime_error("Steps 8..240");
 std::string output=argv[3],checkpoint=argc>4?argv[4]:"";
 bool resume=argc>5&&(std::string(argv[5])=="--resume"||std::string(argv[5])=="--resume-no-save");
 bool save_checkpoint=!checkpoint.empty() && !(argc>5&&std::string(argv[5])=="--resume-no-save");
 int drive_mask=1,slots=64,loadcap=16;
 int seed=1024;
 Scheduler sched(slots,loadcap,seed,drive_mask,learn);
 u32 src=0,dst=0;int slot=-1;float baseline=0;
 for(u32 node=1024*M;node<(1025*M);node++){
  for(int i=24;i<32;i++){
   Edge e=edge(node,i);float w=(float)e.weight/2500.0f;
   if(e.weight>0 && w>=0.70f && w<0.74f) {
    src=node;dst=e.target;slot=i-24;baseline=w;break;
   }
  }
  if(slot>=0)break;
 }
 if(slot<0)throw std::runtime_error("No suitable deterministic cue->readout synapse");
 sched.watched_neuron=dst;
 int first=0;
 if(resume){
  if(checkpoint.empty())throw std::runtime_error("No checkpoint for resume");
  first=sched.load_checkpoint(checkpoint, true);
  if(sched.watched_neuron!=dst)throw std::runtime_error("Readout changed across checkpoint");
 }else{
  if(!sched.test_roundtrip())throw std::runtime_error("GPU roundtrip failed");
  sched.ensure(src/M,0,true);
  sched.ensure(dst/M,0,true);
 }
 auto clock=std::chrono::steady_clock::now();
 for(int t=first;t<steps;t++){
  std::vector<std::pair<u32,float>> stimulus;
  if(cue_at(t,train_cue))stimulus.push_back({src,1.4f});
  if(teacher_enabled && teacher_at(t))stimulus.push_back({dst,1.3f});
  if(t==186)stimulus.push_back({src+1,1.4f}); // novel, unpaired distractor cue
  sched.step(t,false,stimulus);
 }
 if(save_checkpoint)sched.save_checkpoint(checkpoint,steps,true);
 double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-clock).count();
 u64 key=Scheduler::key_for(src,slot);
 auto pre=std::vector<int>{4,10,16}, post=std::vector<int>{158,178};
 int before=sum_probe(sched,pre),after=sum_probe(sched,post);
 int teaching=0;for(int k=0;k<11;k++)teaching+=readout(sched,31+10*k);
 std::ofstream o(output);if(!o)throw std::runtime_error("Result file unavailable");
 o<<"{\n"
   <<"\"format\":\"GENESIS-HQ500M-Q0.8-ASSOCIATION\","
   <<"\"protocol\":\""<<protocol<<"\","
   <<"\"virtual_neurons\":500000000,\"learning_enabled\":"<<(learn?"true":"false")<<","
   <<"\"cue_global_id\":"<<src<<",\"readout_global_id\":"<<dst<<","
   <<"\"gene_slot\":"<<slot+24<<",\"base_weight\":"<<baseline<<","
   <<"\"final_weight_multiplier\":"<<1.0f+sched.delta_of(key)<<","
   <<"\"final_effective_synaptic_weight\":"<<baseline*(1.0f+sched.delta_of(key))<<","
   <<"\"trained_synapse_delta\":"<<sched.delta_of(key)<<","
   <<"\"pretraining_probe_cues\":3,\"pretraining_readout_spikes\":"<<before<<","
   <<"\"paired_training_epochs\":11,\"training_phase_readout_spikes\":"<<teaching<<","
   <<"\"distractor_global_id\":"<<(src+1)<<",\"distractor_readout_spikes\":"<<readout(sched,187)<<","
   <<"\"posttraining_probe_cues\":"<<(steps>178?2:steps>158?1:0)<<","
   <<"\"posttraining_readout_spikes\":"<<after<<","
   <<"\"retention_probe_cues\":"<<(steps>230?2:steps>210?1:0)<<","
   <<"\"retention_readout_spikes\":"<<(readout(sched,211)+readout(sched,231))<<","
   <<"\"learned_synapses_total\":"<<sched.plastic.size()<<","
   <<"\"ltp_updates\":"<<sched.ltp_updates<<",\"ltd_updates\":"<<sched.ltd_updates<<","
   <<"\"external_injections\":"<<sched.external_injections<<","
   <<"\"events_emitted\":"<<sched.born<<",\"events_delivered\":"<<sched.delivered
   <<",\"events_still_pending\":"<<sched.pending.size()<<",\"event_drops\":"<<sched.dropped<<","
   <<"\"steps\":"<<steps<<",\"gpu_count\":8,"
   <<"\"source_synapse_key\":"<<key<<","
   <<"\"readout_spike_steps\":[";
 bool firstspike=true;
 for(size_t t=0;t<sched.watched_spikes_by_step.size();t++)
  if(sched.watched_spikes_by_step[t]>0) {
   o<<(firstspike?"":",")<<t;firstspike=false;
  }
 o<<"],\"spikes_by_gpu\":[";
 for(int d=0;d<G;d++)o<<(d?",":"")<<sched.spikes_by_gpu[d];
 o<<"],\"runtime_seconds\":"<<wall<<"}\n";
 o.close();
 printf("ASSAY Q0.8 protocol=%s pre=%d/3 paired_teacher=%d/11 post=%d/2 delta=%.6f base=%.6f effective=%.6f\n",
  protocol.c_str(),before,teaching,after,sched.delta_of(key),baseline,baseline*(1+sched.delta_of(key)));
 printf("neuron_src=%u exact_neuron_dst=%u gene_slot=%d changed_synapses=%zu ltp=%llu ltd=%llu emitted=%llu delivered=%llu pending=%zu\n",
  src,dst,slot+24,sched.plastic.size(),(unsigned long long)sched.ltp_updates,
  (unsigned long long)sched.ltd_updates,(unsigned long long)sched.born,(unsigned long long)sched.delivered,sched.pending.size());
 return 0;
}
