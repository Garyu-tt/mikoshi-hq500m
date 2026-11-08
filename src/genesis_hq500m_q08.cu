// GENESIS HQ500M Q0.6: demand-paged exact-address GPU microcircuits
// Experimental synthetic network, not a biological human connectome.
// 8 P106 GPUs, module=1024 neurons, fixed slot budgets; no full graph stored.
// When a target is non-resident its real global address is retained in a CPU
// queue. Load-on-demand, evict and restore ALL voltage/refractory/current state.
// Events wait until their real target is available; measured delivery delay.
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <type_traits>
#include <cstring>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using u32=uint32_t;using u64=uint64_t;
constexpr u64 N=500000000ULL,SEED=37421ULL;
constexpr int G=8,M=1024,DEG=32;
constexpr u64 BOUND[8]={0,224999424ULL,294999040ULL,344999936ULL,394999808ULL,434999296ULL,469999616ULL,N};
struct Edge{u32 target; int16_t weight;uint8_t gene,type;};
static_assert(sizeof(Edge)==8);
__host__ __device__ inline u64 mix(u64 x){
 x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
 x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);
}
__host__ __device__ inline int region(u64 x) {
 const u64 b[8]={0,224999424ULL,294999040ULL,344999936ULL,394999808ULL,434999296ULL,469999616ULL,N};
 for(int i=0;i<7;i++)if(x<b[i+1])return i;
 return -1;
}
__host__ __device__ inline Edge edge(u64 src,int s){
 u64 h0=mix(src^SEED),h=mix(h0^((u64)(s+1)*0x517cc1b727220a95ULL));
 int r=region(src);u32 type=(h0%100)<20?1:0;
 u32 dst;uint8_t gene=0;
 if(s<24){
  u64 mb=(src/M)*M;u32 cnt=(u32)(((mb+M)>N)?N-mb:M);
  u32 odd=(u32)(h0>>11)|1U;
  dst=(u32)(mb+((u32)(src-mb)+(u32)(s+1)*odd)%cnt);
 }else{
  const int routes[7]={3,5,0,0,3,1,2};
  int to=routes[r];u64 rb[8]={0,224999424ULL,294999040ULL,344999936ULL,394999808ULL,434999296ULL,469999616ULL,N};
  u64 start=rb[to],end=rb[to+1],nm=(end-start+M-1)/M;
  u64 mb=start+(mix(h^(src/M))%nm)*M;
  u32 cnt=(u32)((end-mb)<M?end-mb:M);
  dst=(u32)(mb+((h>>24)%cnt));gene=(uint8_t)(r+1);
 }
 int16_t w=(int16_t)(300+(h>>33)%4800);
 if(type==1)w=-w;
 return {dst,w,gene,(uint8_t)type};
}
static void ck(cudaError_t x,const char*why){
 if(x!=cudaSuccess){fprintf(stderr,"CUDA %s: %s\n",why,cudaGetErrorString(x));exit(2);}
}
struct Deposit{u32 index;float strength;};
struct State{
 std::array<float,M> voltage{},current{};
 std::array<int,M> refractory{};
 int saved_tick=0;
};
struct Pending{
 u32 src=0,dst=0;
 float strength=0;
 int born=0;
 uint8_t slot=0; // 0..7, the original global C5 edge slot 24..31
};
struct Plastic {float delta=0;u32 ltp=0,ltd=0;};
struct Arrival {u64 key=0;int tick=-1;};

struct Device{
 int id=0,slots=8;
 float *voltage=nullptr,*input=nullptr,*next=nullptr;
 int *refractory=nullptr;
 u32 *spikes=nullptr,*counter=nullptr,*pageids=nullptr;
 Deposit *inbound=nullptr;
 std::vector<u32> pages;
 std::vector<int> last_used;
 std::vector<u32> hspikes;
 std::vector<Deposit> deposits;
 std::vector<int> tick_counts;
 u64 spikes_total=0;
};
static int owner(u32 page){
 u64 addr=(u64)page*M;int r=region(addr);
 if(r==0)return (page%2==0)?0:7;
 return r;
}
static u32 page_id(u32 addr){return addr/M;}
__global__ void deposit_kernel(Deposit*dep,int count,float*input,int total){
 int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<count){Deposit e=dep[i];if(e.index<(u32)total)atomicAdd(&input[e.index],e.strength);}
}
__global__ void lif_kernel(int total,int tick,int start_page,int drive_enabled,
                           const u32 *pages,float*voltage,int*refractory,
                           float*input,float*next,u32*spikes,u32*counter){
 int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i>=total)return;
 int slot=i/M;u32 page=pages[slot];if(page==0xffffffffU)return;
 float impulse=input[i];input[i]=0;
 float v=voltage[i]*0.72f+impulse;
 if(drive_enabled && page==(u32)start_page && tick>=4 && tick<8 && i%M<128)v+=1.4f;
 int ref=refractory[i];
 if(ref>0){refractory[i]=ref-1;voltage[i]=0;return;}
 if(v>1.0f){
  voltage[i]=0;refractory[i]=2;
  u32 pos=atomicAdd(counter,1U);if(pos<(u32)total)spikes[pos]=i;
  u32 src=page*M+(u32)i%M;
  if(src>=N)return;
  float w=(mix(src^SEED)%100)<20?-0.095f:0.090f;
  #pragma unroll
  for(int s=0;s<24;s++){
   Edge e=edge(src,s);
   u32 target_local=e.target%M; // all local edges remain in same module (1024-aligned)
   atomicAdd(&next[slot*M+target_local],w);
  }
 }else voltage[i]=v;
}
static void initialize(std::array<Device,G>&dev,int slots){
 for(int d=0;d<G;d++){
  ck(cudaSetDevice(d),"init set device");
  auto &s=dev[d];s.id=d;s.slots=slots;s.pages.assign(slots,0xffffffffU);
  s.last_used.assign(slots,-1);s.hspikes.resize((size_t)slots*M);
  size_t n=(size_t)slots*M;
  ck(cudaMalloc((void**)&s.voltage,n*sizeof(float)),"voltage");
  ck(cudaMalloc((void**)&s.input,n*sizeof(float)),"input");
  ck(cudaMalloc((void**)&s.next,n*sizeof(float)),"next");
  ck(cudaMalloc((void**)&s.refractory,n*sizeof(int)),"refractory");
  ck(cudaMalloc((void**)&s.spikes,n*sizeof(u32)),"spikes");
  ck(cudaMalloc((void**)&s.counter,sizeof(u32)),"counter");
  ck(cudaMalloc((void**)&s.pageids,slots*sizeof(u32)),"page ids");
  ck(cudaMalloc((void**)&s.inbound,n*8*sizeof(Deposit)),"inbound");
  ck(cudaMemset(s.voltage,0,n*sizeof(float)),"v memset");
  ck(cudaMemset(s.input,0,n*sizeof(float)),"i memset");
  ck(cudaMemset(s.next,0,n*sizeof(float)),"next memset");
  ck(cudaMemset(s.refractory,0,n*sizeof(int)),"ref memset");
  ck(cudaMemcpy(s.pageids,s.pages.data(),slots*sizeof(u32),cudaMemcpyHostToDevice),"initial pages");
  s.deposits.reserve(8192);
 }
}
class Scheduler {
 public:
 std::array<Device,G> devices;
 std::unordered_map<u32,std::pair<int,int>> resident;
 std::unordered_map<u32,State> cold;
 std::deque<Pending> pending;
 // Plastic weights keyed by GLOBAL source neuron ID and original outgoing slot.
 // They persist independently of whether their source/target neuron pages are resident.
 std::unordered_map<u64,Plastic> plastic;
 std::unordered_map<u32,Arrival> last_arrival;
 std::unordered_map<u32,int> last_post;
 u64 ltp_updates=0,ltd_updates=0;
 bool learning_enabled=true;

 u64 born=0,delivered=0,evicted=0,restored=0,initialised=0;
 u64 delayed=0,dropped=0,eviction_bytes=0;
 size_t max_pending=200000;
 int page_loads=0,peak_resident=0,evict_verified=0;
 int slots=0,loadcap=0;
 int drive_page;
 int restored_start_tick=0;
 int drive_mask=1;
 std::array<u32,G> drive_pages{};
 std::vector<std::array<u32,3>> address_samples;
 std::array<u64,G> spikes_by_gpu{};
 std::array<u64,7> delivered_target_region{};
 std::array<u64,7> emitted_target_region{};
 std::vector<int> active_counts,pending_counts;
 u32 watched_neuron=0xffffffffU;
 std::vector<int> watched_spikes_by_step;
 u64 external_injections=0;

 explicit Scheduler(int slots_,int loadcap_,int drivepage,int mask=1,bool learn=true):slots(slots_),loadcap(loadcap_),drive_page(drivepage),drive_mask(mask),learning_enabled(learn){
  initialize(devices,slots);
  for(int d=0;d<G;d++){
   if(d==0)drive_pages[d]=drivepage;
   else if(d==7)drive_pages[d]=1025; // odd cortical module
   else drive_pages[d]=(u32)(BOUND[d]/M+1024);
   if(owner(drive_pages[d])!=d)throw std::runtime_error("Wrong seed owner");
  }
 }
 static u64 key_for(u32 src,int slot){return ((u64)src<<3)|(u64)(slot&7);}
 float delta_of(u64 key)const{
  auto it=plastic.find(key);return it==plastic.end()?0.0f:it->second.delta;
 }
 void potentiation(u64 key,int delta_tick){
  if(!learning_enabled||delta_tick<0||delta_tick>15)return;
  // Excitatory connections only, bounded pair-based time window.
  float amplitude=0.065f*std::exp(-float(delta_tick)/8.0f);
  auto &syn=plastic[key];syn.delta=std::min(0.80f,std::max(-0.70f,syn.delta+amplitude));
  syn.ltp++;ltp_updates++;
 }
 void depression(u64 key,int delta_tick){
  if(!learning_enabled||delta_tick<0||delta_tick>15)return;
  float amplitude=0.022f*std::exp(-float(delta_tick)/8.0f);
  auto &syn=plastic[key];syn.delta=std::min(0.80f,std::max(-0.70f,syn.delta-amplitude));
  syn.ltd++;ltd_updates++;
 }
 void note_arrival(u32 destination,u64 key,int tick){
  if(learning_enabled)last_arrival[destination]={key,tick};
 }
 void post_spike(u32 destination,int tick){
  if(!learning_enabled)return;
  auto found=last_arrival.find(destination);
  if(found!=last_arrival.end()){
   int age=tick-found->second.tick;
   if(age>=0 && age<=15)potentiation(found->second.key,age);
   last_arrival.erase(found); // one association per delivered event
  }
  last_post[destination]=tick;
 }
 void prune_traces(int tick){
  if(!learning_enabled||tick%16)return;
  for(auto it=last_arrival.begin();it!=last_arrival.end();)
   if(tick-it->second.tick>15)it=last_arrival.erase(it);else ++it;
  for(auto it=last_post.begin();it!=last_post.end();)
   if(tick-it->second>15)it=last_post.erase(it);else ++it;
 }
 double delta_abs_sum()const{
  double x=0;for(auto &kv:plastic)x+=std::abs((double)kv.second.delta);return x;
 }
 void save_slot(int d,int slot,int now){
  auto &dev=devices[d];u32 page=dev.pages[slot];
  if(page==0xffffffffU)return;
  ck(cudaSetDevice(d),"save device");
  State value{};size_t pos=(size_t)slot*M;
  ck(cudaMemcpy(value.voltage.data(),dev.voltage+pos,M*sizeof(float),cudaMemcpyDeviceToHost),"read V");
  ck(cudaMemcpy(value.current.data(),dev.input+pos,M*sizeof(float),cudaMemcpyDeviceToHost),"read I");
  ck(cudaMemcpy(value.refractory.data(),dev.refractory+pos,M*sizeof(int),cudaMemcpyDeviceToHost),"read refrac");
  value.saved_tick=now;
  cold[page]=value;
  eviction_bytes+=sizeof(State);evicted++;
  resident.erase(page);
  dev.pages[slot]=0xffffffffU;dev.last_used[slot]=-1;
 }
 int ensure(u32 page,int now,bool pin_drive){
  auto hit=resident.find(page);
  if(hit!=resident.end()){auto [d,slot]=hit->second;devices[d].last_used[slot]=now;return d;}
  int d=owner(page);auto &dev=devices[d];
  int slot=-1;
  for(int j=0;j<slots;j++)if(dev.pages[j]==0xffffffffU){slot=j;break;}
  if(slot<0){
   int oldest=std::numeric_limits<int>::max();
   for(int j=0;j<slots;j++){
    if(pin_drive && (drive_mask&(1<<d)) && dev.pages[j]==drive_pages[d])continue;
    if(dev.last_used[j]==now)continue; // never evict a module with events scheduled this step
    if(dev.last_used[j]<oldest){oldest=dev.last_used[j];slot=j;}
   }
   if(slot<0)return -1; // postpone event, never inject into a stale/reused slot
   save_slot(d,slot,now);
  }
  State state{};
  auto found=cold.find(page);
  if(found!=cold.end()){
   state=found->second;
   // Offline refractory recovery and leaky membrane relaxation in wall-free ticks;
   // no network input is generated for an inactive module.
   int age=std::max(0,now-state.saved_tick);
   if(age){
    float decay=std::pow(0.72f,std::min(50,age));
    for(int i=0;i<M;i++){
     state.voltage[i]*=decay;
     state.current[i]=0;
     state.refractory[i]=std::max(0,state.refractory[i]-age);
    }
   }
   cold.erase(found);restored++;
  }else initialised++;
  ck(cudaSetDevice(d),"load device");
  size_t pos=(size_t)slot*M;
  ck(cudaMemcpy(dev.voltage+pos,state.voltage.data(),M*sizeof(float),cudaMemcpyHostToDevice),"load V");
  ck(cudaMemcpy(dev.input+pos,state.current.data(),M*sizeof(float),cudaMemcpyHostToDevice),"load I");
  ck(cudaMemcpy(dev.refractory+pos,state.refractory.data(),M*sizeof(int),cudaMemcpyHostToDevice),"load refractory");
  ck(cudaMemset(dev.next+pos,0,M*sizeof(float)),"clear next slot");
  dev.pages[slot]=page;dev.last_used[slot]=now;
  ck(cudaMemcpy(dev.pageids+slot,&page,sizeof(u32),cudaMemcpyHostToDevice),"page directory");
  resident[page]={d,slot};
  page_loads++;peak_resident=std::max(peak_resident,(int)resident.size());
  return d;
 }
 void deliver_events(int tick) {
  std::array<int,G> loads{};
  for(auto &dev:devices)dev.deposits.clear();
  // Readout-salience queue: preserve all exact addresses but service the
  // explicitly monitored neuron first, for both learning and ablation runs.
  // Without it a large cold-event backlog can starve a cue probe indefinitely.
  if(watched_neuron<N)
   std::stable_partition(pending.begin(),pending.end(),
      [&](const Pending &e){return e.dst==watched_neuron;});
  // Rotate past unaffordable modules: no aliasing, preserve full exact Pending event.
  size_t count=pending.size();
  for(size_t k=0;k<count;k++){
   auto event=pending.front();pending.pop_front();
   u32 page=page_id(event.dst);int d=owner(page);
   bool hit=resident.find(page)!=resident.end();
   if(!hit && loads[d]>=loadcap){pending.push_back(event);continue;}
   if(!hit){if(ensure(page,tick,true)<0){pending.push_back(event);continue;} loads[d]++;}
   auto entry=resident.at(page);
   devices[d].last_used[entry.second]=tick;
   int targetSlot=entry.second;
   devices[d].deposits.push_back({(u32)(targetSlot*M+(event.dst%M)),event.strength});
   if(learning_enabled && event.strength>0)
    note_arrival(event.dst,key_for(event.src,event.slot),tick);
   delivered++;delayed+=tick-event.born;
   delivered_target_region[region(event.dst)]++;
   if(address_samples.size()<120)
    address_samples.push_back({event.src,event.dst,(u32)tick});
  }
  for(int d=0;d<G;d++){
   auto &dev=devices[d];
   if(!dev.deposits.empty()){
    ck(cudaSetDevice(d),"deposit device");
    size_t n=dev.deposits.size(),cap=(size_t)slots*M*8;
    if(n>cap)throw std::runtime_error("Inbound buffer overrun");
    ck(cudaMemcpy(dev.inbound,dev.deposits.data(),n*sizeof(Deposit),cudaMemcpyHostToDevice),"copy deposits");
    deposit_kernel<<<(n+255)/256,256>>>(dev.inbound,(int)n,dev.input,(int)slots*M);
    ck(cudaGetLastError(),"deposit kernel");
   }
  }
 }
 void step(int tick,bool stimulate,const std::vector<std::pair<u32,float>>& input_stimuli={}){
  deliver_events(tick);
  // External signals are identified by exact virtual neuron IDs and injected
  // after the ordinary queue's paging decisions (no modulo-folding).
  for(auto [target,amp]:input_stimuli){
   if(target>=N||!std::isfinite(amp)||amp<=0)throw std::runtime_error("Invalid sensory stimulus");
   u32 page=page_id(target);
   if(!resident.count(page) && ensure(page,tick,true)<0)
    throw std::runtime_error("Insufficient GPU slots for sensory stimulus");
   int d=owner(page),slot=resident.at(page).second;
   devices[d].last_used[slot]=tick;
   Deposit dep{(u32)(slot*M+target%M),amp};
   ck(cudaSetDevice(d),"external input device");
   ck(cudaMemcpy(devices[d].inbound,&dep,sizeof(dep),cudaMemcpyHostToDevice),"external signal");
   deposit_kernel<<<1,1>>>(devices[d].inbound,1,devices[d].input,(int)slots*M);
   ck(cudaGetLastError(),"external input kernel");
   external_injections++;
  }
  std::array<u32,G> count{};
  for(int d=0;d<G;d++){
   ck(cudaSetDevice(d),"step gpu");
   auto &dev=devices[d];
   ck(cudaMemset(dev.counter,0,sizeof(u32)),"counter reset");
   ck(cudaMemset(dev.next,0,(size_t)slots*M*sizeof(float)),"next reset");
   lif_kernel<<<(slots*M+255)/256,256>>>(slots*M,tick,(int)drive_pages[d],(stimulate && (drive_mask&(1<<d)))?1:0,
    dev.pageids,dev.voltage,dev.refractory,dev.input,dev.next,dev.spikes,dev.counter);
   ck(cudaGetLastError(),"LIF kernel");
  }
  for(int d=0;d<G;d++){
   ck(cudaSetDevice(d),"count gpu");
   auto &dev=devices[d];
   ck(cudaMemcpy(&count[d],dev.counter,sizeof(u32),cudaMemcpyDeviceToHost),"spike count");
   if(count[d]>(u32)slots*M)throw std::runtime_error("Impossible spike count");
   if(count[d]){
    ck(cudaMemcpy(dev.hspikes.data(),dev.spikes,count[d]*sizeof(u32),cudaMemcpyDeviceToHost),"read spike IDs");
    // CUDA atomicAdd determines discovery order nondeterministically.
    // Canonical order removes nondeterministic module paging decisions.
    std::sort(dev.hspikes.begin(),dev.hspikes.begin()+count[d]);
   }
   if(watched_neuron<N){
    for(u32 k=0;k<count[d];k++){
     u32 idx=dev.hspikes[k];u32 pg=dev.pages[idx/M];
     if(pg!=0xffffffffU && (u64)pg*M+idx%M==watched_neuron){
      if(watched_spikes_by_step.size()<=((size_t)tick))watched_spikes_by_step.resize(tick+1,0);
      watched_spikes_by_step[tick]++;
     }
    }
   }
   dev.tick_counts.push_back((int)count[d]);spikes_by_gpu[d]+=count[d];
  }
  prune_traces(tick);
  for(int d=0;d<G;d++){
   auto &dev=devices[d];
   for(u32 k=0;k<count[d];k++){
    u32 idx=dev.hspikes[k],slot=idx/M;
    u32 page=dev.pages[slot];if(page==0xffffffffU)throw std::runtime_error("fired inactive page");
    u32 src=page*M+idx%M;
    post_spike(src,tick);
    // Strict actual target addresses, none folded onto representative modules.
    for(int s=24;s<32;s++){
     Edge e=edge(src,s);
     u64 key=key_for(src,s-24);
     if(learning_enabled && e.weight>0){
      auto seen=last_post.find(e.target);
      if(seen!=last_post.end() && tick>=seen->second)
        depression(key,tick-seen->second);
     }
     float strength=((float)e.weight/2500.0f)*(1.0f+delta_of(key));
     if(pending.size()>=max_pending)throw std::runtime_error("Pending capacity reached, no events discarded");
     pending.push_back({src,e.target,strength,tick,(uint8_t)(s-24)});born++;
     emitted_target_region[region(e.target)]++;
    }
   }
  }
  for(int d=0;d<G;d++){
   ck(cudaSetDevice(d),"swap device");
   ck(cudaDeviceSynchronize(),"GPU synchronized");
   std::swap(devices[d].input,devices[d].next);
  }
  active_counts.push_back((int)resident.size());
  pending_counts.push_back((int)pending.size());
 }
 // deterministic state preservation test: read before eviction, force reload same tick.
 bool test_roundtrip(){
  u32 first=page_id((u32)drive_page*M);
  ensure(first,0,false);
  int d=owner(first),slot=resident.at(first).second;
  State custom{};
  for(int i=0;i<M;i++){custom.voltage[i]=(i%71)*0.01f;custom.current[i]=(i%37)*0.002f;custom.refractory[i]=i%4;}
  ck(cudaSetDevice(d),"roundtrip device");
  ck(cudaMemcpy(devices[d].voltage+(size_t)slot*M,custom.voltage.data(),M*sizeof(float),cudaMemcpyHostToDevice),"test V");
  ck(cudaMemcpy(devices[d].input+(size_t)slot*M,custom.current.data(),M*sizeof(float),cudaMemcpyHostToDevice),"test I");
  ck(cudaMemcpy(devices[d].refractory+(size_t)slot*M,custom.refractory.data(),M*sizeof(int),cudaMemcpyHostToDevice),"test R");
  save_slot(d,slot,0);
  ensure(first,0,false);
  auto [d2,slot2]=resident.at(first);State after{};
  ck(cudaMemcpy(after.voltage.data(),devices[d2].voltage+(size_t)slot2*M,M*sizeof(float),cudaMemcpyDeviceToHost),"check V");
  ck(cudaMemcpy(after.current.data(),devices[d2].input+(size_t)slot2*M,M*sizeof(float),cudaMemcpyDeviceToHost),"check I");
  ck(cudaMemcpy(after.refractory.data(),devices[d2].refractory+(size_t)slot2*M,M*sizeof(int),cudaMemcpyDeviceToHost),"check R");
  bool good=custom.voltage==after.voltage && custom.current==after.current &&
     custom.refractory==after.refractory;
  // Return to clean initial state for stimulus test.
  State zero{};
  ck(cudaMemcpy(devices[d2].voltage+(size_t)slot2*M,zero.voltage.data(),M*sizeof(float),cudaMemcpyHostToDevice),"reset V");
  ck(cudaMemcpy(devices[d2].input+(size_t)slot2*M,zero.current.data(),M*sizeof(float),cudaMemcpyHostToDevice),"reset I");
  ck(cudaMemcpy(devices[d2].refractory+(size_t)slot2*M,zero.refractory.data(),M*sizeof(int),cudaMemcpyHostToDevice),"reset R");
  evict_verified=good?1:0;return good;
 }

 template<typename T>static void wr(std::ostream&out,const T&v){
  static_assert(std::is_trivially_copyable<T>::value,"checkpoint POD only");
  out.write(reinterpret_cast<const char*>(&v),sizeof(T));if(!out)throw std::runtime_error("Checkpoint write failed");
 }
 template<typename T>static void rd(std::istream&in,T &v){
  static_assert(std::is_trivially_copyable<T>::value,"checkpoint POD only");
  in.read(reinterpret_cast<char*>(&v),sizeof(T));if(!in)throw std::runtime_error("Checkpoint truncated");
 }
 template<typename T>static void write_vector(std::ostream&o,const std::vector<T>&x){
  u64 n=x.size();wr(o,n);
  if(n>0){o.write((const char*)x.data(),n*sizeof(T));if(!o)throw std::runtime_error("Write vector failed");}
 }
 template<typename T>static void read_vector(std::istream&i,std::vector<T>&x,u64 maxn){
  u64 n=0;rd(i,n);
  if(n>maxn)throw std::runtime_error("Checkpoint vector too large");
  x.resize((size_t)n);
  if(n){i.read((char*)x.data(),n*sizeof(T));if(!i)throw std::runtime_error("Read vector failed");}
 }
 void save_checkpoint(const std::string&file,int endtick,bool stimulus){
  std::string partial=file+".tmp";
  std::ofstream o(partial,std::ios::binary|std::ios::trunc);
  if(!o)throw std::runtime_error("Failed checkpoint open");
  char magic[24]="HQ500M_Q08_CHK_V1";
  o.write(magic,24);
  u64 vN=N,vSeed=SEED;wr(o,vN);wr(o,vSeed);
  wr(o,endtick);wr(o,slots);wr(o,loadcap);wr(o,stimulus);wr(o,drive_mask);wr(o,learning_enabled);
  wr(o,born);wr(o,delivered);wr(o,evicted);wr(o,restored);wr(o,initialised);
  wr(o,delayed);wr(o,dropped);wr(o,eviction_bytes);
  wr(o,page_loads);wr(o,peak_resident);wr(o,evict_verified);
  wr(o,spikes_by_gpu);wr(o,delivered_target_region);wr(o,emitted_target_region);
  write_vector(o,active_counts);write_vector(o,pending_counts);write_vector(o,address_samples);
  u64 np=pending.size();wr(o,np);
  for(auto& e:pending)wr(o,e);
  std::vector<u32> keys;keys.reserve(cold.size());
  for(auto &v:cold)keys.push_back(v.first);
  std::sort(keys.begin(),keys.end());
  u64 nc=keys.size();wr(o,nc);
  for(auto key:keys){wr(o,key);wr(o,cold.at(key));}
  wr(o,watched_neuron);wr(o,external_injections);
  write_vector(o,watched_spikes_by_step);
  wr(o,ltp_updates);wr(o,ltd_updates);
  std::vector<u64> plastic_ids;plastic_ids.reserve(plastic.size());
  for(auto &x:plastic)plastic_ids.push_back(x.first);
  std::sort(plastic_ids.begin(),plastic_ids.end());
  u64 pc=plastic_ids.size();wr(o,pc);
  for(auto key:plastic_ids){wr(o,key);wr(o,plastic.at(key));}
  std::vector<u32> trace_ids;
  trace_ids.reserve(last_arrival.size());
  for(auto &x:last_arrival)trace_ids.push_back(x.first);
  std::sort(trace_ids.begin(),trace_ids.end());
  u64 ac=trace_ids.size();wr(o,ac);
  for(auto key:trace_ids){wr(o,key);wr(o,last_arrival.at(key));}
  trace_ids.clear();
  for(auto &x:last_post)trace_ids.push_back(x.first);
  std::sort(trace_ids.begin(),trace_ids.end());
  u64 sc=trace_ids.size();wr(o,sc);
  for(auto key:trace_ids){wr(o,key);wr(o,last_post.at(key));}
  for(int d=0;d<G;d++){
   auto &dev=devices[d];
   write_vector(o,dev.tick_counts);
   for(int slot=0;slot<slots;slot++){
    u32 page=dev.pages[slot];wr(o,page);wr(o,dev.last_used[slot]);
    if(page!=0xffffffffU){
     ck(cudaSetDevice(d),"checkpoint device");
     State state{};size_t pos=(size_t)slot*M;
     ck(cudaMemcpy(state.voltage.data(),dev.voltage+pos,M*sizeof(float),cudaMemcpyDeviceToHost),"checkpoint V");
     ck(cudaMemcpy(state.current.data(),dev.input+pos,M*sizeof(float),cudaMemcpyDeviceToHost),"checkpoint I");
     ck(cudaMemcpy(state.refractory.data(),dev.refractory+pos,M*sizeof(int),cudaMemcpyDeviceToHost),"checkpoint refractory");
     state.saved_tick=endtick;wr(o,state);
    }
   }
  }
  o.flush();if(!o)throw std::runtime_error("Checkpoint flush failed");
  o.close();
  if(std::rename(partial.c_str(),file.c_str())!=0)throw std::runtime_error("Checkpoint rename failed");
 }
 int load_checkpoint(const std::string&file,bool stimulus){
  std::ifstream i(file,std::ios::binary);
  if(!i)throw std::runtime_error("Checkpoint not found");
  char magic[24]{};i.read(magic,24);
  if(std::memcmp(magic,"HQ500M_Q08_CHK_V1",18)!=0)throw std::runtime_error("Checkpoint version mismatch");
  u64 vn,vseed;rd(i,vn);rd(i,vseed);
  if(vn!=N||vseed!=SEED)throw std::runtime_error("Checkpoint genome mismatch");
  int endtick,cs,cc,mask;bool stim,learn;
  rd(i,endtick);rd(i,cs);rd(i,cc);rd(i,stim);rd(i,mask);rd(i,learn);
  if(endtick<0||endtick>500||cs!=slots||cc!=loadcap||stim!=stimulus||mask!=drive_mask||learn!=learning_enabled)
    throw std::runtime_error("Checkpoint parameters mismatch");
  rd(i,born);rd(i,delivered);rd(i,evicted);rd(i,restored);rd(i,initialised);
  rd(i,delayed);rd(i,dropped);rd(i,eviction_bytes);
  rd(i,page_loads);rd(i,peak_resident);rd(i,evict_verified);
  rd(i,spikes_by_gpu);rd(i,delivered_target_region);rd(i,emitted_target_region);
  read_vector(i,active_counts,501);read_vector(i,pending_counts,501);read_vector(i,address_samples,120);
  u64 np;rd(i,np);if(np>max_pending)throw std::runtime_error("Pending queue too large");
  pending.clear();for(u64 k=0;k<np;k++){Pending e;rd(i,e);pending.push_back(e);}
  u64 nc;rd(i,nc);if(nc>50000)throw std::runtime_error("Too many cold snapshots");
  cold.clear();
  for(u64 k=0;k<nc;k++){u32 key;State state{};rd(i,key);rd(i,state);if(key>=((N+M-1)/M))throw std::runtime_error("Bad cold page");cold[key]=state;}
  rd(i,watched_neuron);rd(i,external_injections);
  read_vector(i,watched_spikes_by_step,501);
  rd(i,ltp_updates);rd(i,ltd_updates);
  u64 pc=0;rd(i,pc);if(pc>500000)throw std::runtime_error("Too many plastic synapses");
  plastic.clear();
  for(u64 k=0;k<pc;k++){u64 key;Plastic value{};rd(i,key);rd(i,value);
   if(key>=(N<<3)||value.delta>0.80f||value.delta< -0.70f)throw std::runtime_error("Bad plastic weight");
   plastic[key]=value;}
  u64 ac=0;rd(i,ac);if(ac>200000)throw std::runtime_error("Too many arrival traces");
  last_arrival.clear();
  for(u64 k=0;k<ac;k++){u32 key;Arrival value{};rd(i,key);rd(i,value);
   if(key>=N)throw std::runtime_error("Bad arrival addr");last_arrival[key]=value;}
  u64 sc=0;rd(i,sc);if(sc>200000)throw std::runtime_error("Too many post traces");
  last_post.clear();
  for(u64 k=0;k<sc;k++){u32 key;int value;rd(i,key);rd(i,value);
   if(key>=N)throw std::runtime_error("Bad post addr");last_post[key]=value;}
  resident.clear();
  for(int d=0;d<G;d++){
   auto&dev=devices[d];
   read_vector(i,dev.tick_counts,501);
   for(int slot=0;slot<slots;slot++){
    u32 page;int last;rd(i,page);rd(i,last);
    dev.pages[slot]=page;dev.last_used[slot]=last;
    if(page!=0xffffffffU){
     if(owner(page)!=d)throw std::runtime_error("Bad resident owner");
     if(resident.count(page)||cold.count(page))throw std::runtime_error("Duplicate checkpoint page");
     State state{};rd(i,state);resident[page]={d,slot};
     ck(cudaSetDevice(d),"resume device");size_t pos=(size_t)slot*M;
     ck(cudaMemcpy(dev.voltage+pos,state.voltage.data(),M*sizeof(float),cudaMemcpyHostToDevice),"resume V");
     ck(cudaMemcpy(dev.input+pos,state.current.data(),M*sizeof(float),cudaMemcpyHostToDevice),"resume I");
     ck(cudaMemcpy(dev.refractory+pos,state.refractory.data(),M*sizeof(int),cudaMemcpyHostToDevice),"resume refractory");
    }
   }
   ck(cudaSetDevice(d),"resume page directory");
   ck(cudaMemcpy(dev.pageids,dev.pages.data(),slots*sizeof(u32),cudaMemcpyHostToDevice),"resume pages");
  }
  if(i.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Checkpoint trailing bytes");
  if(born!=delivered+pending.size()+dropped)throw std::runtime_error("Broken queue accounting checkpoint");
  restored_start_tick=endtick;return endtick;
 }
 void write_report(const std::string &path,int ticks,int slots,int cap,double seconds,bool stimulated){
  std::ofstream f(path);if(!f)throw std::runtime_error("Cannot save report");
  f<<"{\n\"format\":\"GENESIS-HQ500M-Q0.8\", \"synthetic\":true,"
   <<"\n\"virtual_neurons\":500000000,\"addressable_synapses\":16000000000,"
   <<"\n\"gpu_count\":8,\"module_neurons\":1024,\"slots_per_gpu\":"<<slots<<",\"drive_mask\":"<<drive_mask<<","
   <<"\n\"peak_resident_modules\":"<<peak_resident<<",\"peak_resident_neurons\":"<<peak_resident*M<<","
   <<"\n\"max_active_neurons\":"<<slots*8*M<<",\"steps\":"<<ticks<<",\"stimulated\":"<<(stimulated?"true":"false")<<","
   <<"\n\"watched_neuron\":"<<watched_neuron
   <<",\"external_injections\":"<<external_injections<<","
   <<"\n\"learning_enabled\":"<<(learning_enabled?"true":"false")
   <<",\n\"learned_synapses\":"<<plastic.size()
   <<",\"ltp_updates\":"<<ltp_updates
   <<",\"ltd_updates\":"<<ltd_updates
   <<",\"learned_delta_abs_sum\":"<<delta_abs_sum()<<","
   <<"\n\"events_generated\":"<<born<<",\"events_delivered_exact\":"<<delivered<<","
   <<"\n\"events_pending_undelivered\":"<<pending.size()<<",\"events_dropped\":"<<dropped<<","
   <<"\n\"delivery_wait_steps_total\":"<<delayed<<",\"loaded_module_operations\":"<<page_loads<<","
   <<"\n\"new_modules\":"<<initialised<<",\"modules_evicted\":"<<evicted<<",\"modules_restored\":"<<restored<<","
   <<"\n\"gpu_state_roundtrip_verified\":"<<(evict_verified?"true":"false")<<","
   <<"\n\"retained_cold_module_snapshots\":"<<cold.size()<<","
   <<"\n\"wall_seconds\":"<<std::fixed<<std::setprecision(4)<<seconds<<","
   <<"\n\"synaptic_policy\":\"exact_global_target_id; pending events held in RAM until exact module loaded; no remapping\","
   <<"\n\"offline_decay_policy\":\"voltage exponential decay while unloaded; no simulation of inactive neurons\","
   <<"\n\"spikes_by_gpu\":[";
  for(int d=0;d<G;d++)f<<(d?",":"")<<spikes_by_gpu[d];
  f<<"],\n\"events_emitted_by_region\":[";
  for(int d=0;d<7;d++)f<<(d?",":"")<<emitted_target_region[d];
  f<<"],\n\"events_delivered_by_region\":[";
  for(int d=0;d<7;d++)f<<(d?",":"")<<delivered_target_region[d];
  f<<"],\n\"active_modules_by_step\":[";
  for(size_t i=0;i<active_counts.size();i++)f<<(i?",":"")<<active_counts[i];
  f<<"],\n\"pending_events_by_step\":[";
  for(size_t i=0;i<pending_counts.size();i++)f<<(i?",":"")<<pending_counts[i];
  f<<"],\n\"address_samples\":[";
  for(size_t i=0;i<address_samples.size();i++){
   auto a=address_samples[i];f<<(i?",":"")<<"["<<a[0]<<","<<a[1]<<","<<a[2]<<"]";
  }
  f<<"],\n\"watched_spikes_by_step\":[";
  for(size_t k=0;k<watched_spikes_by_step.size();k++)
   f<<(k?",":"")<<watched_spikes_by_step[k];
  f<<"],\n\"plastic_samples\":[";
  std::vector<u64> learned_ids;learned_ids.reserve(plastic.size());
  for(auto &kv:plastic)learned_ids.push_back(kv.first);
  std::sort(learned_ids.begin(),learned_ids.end());
  for(size_t k=0;k<std::min((size_t)120,learned_ids.size());k++){
   u64 key=learned_ids[k];auto z=plastic.at(key);
   f<<(k?",":"")<<"["<<(key>>3)<<","<<(key&7)<<","<<z.delta<<","<<z.ltp<<","<<z.ltd<<"]";
  }
  f<<"],\n\"pending_sample\":[";
  size_t n=0;for(auto &e:pending){if(n++>=120)break;f<<(n>1?",":"")<<"["<<e.src<<","<<e.dst<<","<<e.born<<"]";}
  f<<"]\n}\n";
 }
};
int main(int argc,char **argv){
 int ticks=argc>1?atoi(argv[1]):48;
 int slots=argc>2?atoi(argv[2]):8;
 int cap=argc>3?atoi(argv[3]):4;
 std::string path=argc>4?argv[4]:"/tmp/HQ500M_Q06.json";
 bool stimulate=argc>5?atoi(argv[5])!=0:true;
 std::string checkpoint=argc>6?argv[6]:"";
 bool resume=argc>7 && std::string(argv[7])=="--resume";
 int drive_mask=argc>8?atoi(argv[8]):1;
 bool learning=argc>9?atoi(argv[9])!=0:true;
 if(drive_mask<=0||drive_mask>255)throw std::runtime_error("Invalid drive mask");
 if(ticks<8||ticks>200||slots<2||slots>64||cap<1||cap>slots){fprintf(stderr,"Usage: %s ticks slots_per_gpu loads_per_gpu_per_tick output.json stimulus[0|1]\n",argv[0]);return 2;}
 int count=0;ck(cudaGetDeviceCount(&count),"get GPU count");
 if(count<G){fprintf(stderr,"Requires 8 GPUs, found %d\n",count);return 2;}
 // Seed is in cortex, on GPU0 (even 1024-page).
 int seed_page=1024;
 Scheduler sched(slots,cap,seed_page,drive_mask,learning);
 int start_tick=0;
 if(resume){
  if(checkpoint.empty())throw std::runtime_error("Resume checkpoint filename missing");
  start_tick=sched.load_checkpoint(checkpoint,stimulate);
  if(start_tick>=ticks)throw std::runtime_error("Requested ticks must exceed checkpoint tick");
 }else{
  if(!sched.test_roundtrip())throw std::runtime_error("State roundtrip failed");
  for(int d=0;d<G;d++)if(drive_mask&(1<<d)){
   if(sched.resident.count(sched.drive_pages[d])==0)sched.ensure(sched.drive_pages[d],0,true);
  }
 }
 auto start=std::chrono::steady_clock::now();
 for(int t=start_tick;t<ticks;t++)sched.step(t,stimulate);
 if(!checkpoint.empty())sched.save_checkpoint(checkpoint,ticks,stimulate);
 double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 sched.write_report(path,ticks,slots,cap,elapsed,stimulate);
 u64 spikes=0;for(auto c:sched.spikes_by_gpu)spikes+=c;
 printf("GENESIS Q0.8 8GPU dynamic pages, virtual=500M resident_peak=%d neurons, modules_loaded=%d,\n"
        "spikes=%llu generated=%llu delivered=%llu queued=%zu evicted=%llu restored=%llu "
        "state_roundtrip=%s, dropped=%llu, runtime=%.3fs\n",
   sched.peak_resident*M,sched.page_loads,(unsigned long long)spikes,
   (unsigned long long)sched.born,(unsigned long long)sched.delivered,
   sched.pending.size(),(unsigned long long)sched.evicted,(unsigned long long)sched.restored,
   sched.evict_verified?"PASS":"FAIL",(unsigned long long)sched.dropped,elapsed);
 for(int d=0;d<G;d++)
   printf("GPU%d spike=%llu modules=%d\n",d,(unsigned long long)sched.spikes_by_gpu[d],
     (int)std::count_if(sched.devices[d].pages.begin(),sched.devices[d].pages.end(),[](u32 p){return p!=0xffffffffU;}));
 if(sched.born!=sched.delivered+sched.pending.size()+sched.dropped){fprintf(stderr,"ACCOUNTING FAIL\n");return 4;}
 return 0;
}
