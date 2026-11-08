#include "hq500m_q09_trial_impl.cu"
int main(int argc,char**argv){
 int lo=argc>1?atoi(argv[1]):0;
 int hi=argc>2?atoi(argv[2]):11;
 if(lo<0 || hi>23 || lo>hi){fprintf(stderr,"Usage: cohort_batch first_id last_id; 0..23\n");return 2;}
 // CUDA allocations intentionally reused at process-wide runtime, but Scheduler
 // does not free its GPU buffers on destruction. Batch max 6 trials x 4 modes
 // to bound the leak until process termination (<200MB/GPU on tests).
 if(hi-lo+1>6)throw std::runtime_error("Batch too large; bound CUDA buffers");
 for(int trial=lo;trial<=hi;trial++){
  for(auto mode:{"on","off","unpaired","cueonly"}){
   char filename[256];std::snprintf(filename,sizeof(filename),"q09_cohort/trial%02d_%s.json",trial,mode);
   char* av[8];
   char steps[]="240", checkpoint[]="-",resume[]="unused";
   char id[16];std::snprintf(id,sizeof(id),"%d",trial);
   av[0]=(char*)"hq500m_q09_cohort_batch";
   av[1]=(char*)mode;
   av[2]=steps;av[3]=filename;av[4]=checkpoint;av[5]=resume;av[6]=id;av[7]=nullptr;
   int rc=q09_cohort_trial_main(7,av);
   if(rc){fprintf(stderr,"Q0.9 failed trial=%d mode=%s exit=%d\n",trial,mode,rc);return rc;}
  }
  printf("Q09 FULL TRIAL %d DONE\n",trial);std::fflush(stdout);
 }
 return 0;
}
