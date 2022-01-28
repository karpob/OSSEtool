#!/usr/bin/env python
#
# module load python/GEOSpyD/Min4.9.2_py3.9 
#
# Script for 
# 1) read requirement from output
# 2) read times, lats and lons from txt files
# 2) read variables from nature run sample Netcdf files given lats, lons and times
# 3) write variable with lats, lons and time to Netcdf file
# Usage:  
#

import yaml
import multiprocessing as mp

from OSSE_helper import *

   
if __name__ == '__main__' :
 
   # load input yaml
   stream = open("input.yaml", 'r')
   config = yaml.full_load(stream)

   # driven by output
   start_time = datetime.fromisoformat(str(config['output']['start_time']))
   end_time   = datetime.fromisoformat(str(config['output']['end_time']))
   #out_duration = end_time-start_time
   out_duration = timedelta(seconds = int(config['output']['duration']))

   while ( start_time < end_time):

     end_time_ = start_time + out_duration
     lats, lons, seconds_increase = read_sat_data(config['locations'], start_time, end_time_)

     manager = mp.Manager()
     var_dict = manager.dict()
     processes = []
     # read variables 
     model_fields = config['input_fields']
     for fields in model_fields :
        for var_names, ins in fields.items():
           cname = ins['collection']
           collections = config['collections']
           collection_ = collections[cname]
           process = mp.Process(target = read_vars_from_collection,  \
                               args=(var_names, collection_, start_time, end_time_, lats, lons, seconds_increase, var_dict))
           processes.append(process)
           #process.start()
     print("\nChunking....")
     nthreads = 15
     chunks = []
     chunk = []
     ii=0
     for p in processes:
        if(ii<nthreads):
           chunk.append(p)
           ii +=1
        else:
           chunk.append(p)
           chunks.append(chunk)
           chunk = []
           ii=0
     if(len(chunk)!=0):
        chunks.append(chunk)
     for c in chunks:
        for ip,p in enumerate(c):
           print("starting thread {}".format(ip))
           p.start()
        for ip,p in enumerate(c):
           p.join()
           print("finished thread {}".format(ip))
        print("next chunk")      
     # write out variables
     out_fname = get_filename_from_tpl(config['output']['template'], start_time + timedelta(hours=3) )
     print("Writing " + out_fname)
     write_variables(out_fname, start_time, var_dict, lats, lons, seconds_increase)

     var_dict.clear()
     lats.clear()
     lons.clear()
     seconds_increase.clear()
     start_time = start_time + out_duration
