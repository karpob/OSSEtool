#!/usr/bin/env python
#
# module load python/GEOSpyD/Ana2019.03_py3.7
#
# Script for 
# 1) read require ment from output
# 2) read times, lats and lons from txt files
# 2) read variables from a nature run sample Netcdf file given lats, lons and times
# 3) write variable with lats, lons and time to Netcdf file
# Usage:  
#

import sys
import os
import yaml
import numpy as np
import multiprocessing as mp

from netCDF4 import Dataset
from datetime import datetime
from datetime import timedelta
from OSSE_get_helper import *

def read_variables(fname, start_time, var_list, lats, lons):
   # verify time and fname or time stamp in file
   fh = Dataset(fname,mode='r')
   n_level = fh.dimensions['lev'].size    
   n_lat = fh.dimensions['lat'].size
   n_lon = fh.dimensions['lon'].size
   dlat = 180.0/n_lat
   dlon = 360.0/n_lon
  
   Is =((np.array(lats)+90.0 )/dlat).astype('int32')
   Js =((np.array(lons)+180.0)/dlon).astype('int32')
   variables =[]
   for i in range(len(var_list)):
      var_name =  var_list[i]
      var_in = fh.variables[var_name][:, :, :, :]
      var = np.ndarray(shape=(n_level, len(Is)))
      for k in range(len(Is)):
        var[:,k] = var_in[0,:,Is[k],Js[k]]
      variables.append((var_name, n_level, var, fh.variables[var_name].__dict__))
   return variables

def read_variables_para(fname, start_time, var_list, lats, lons, var_dict):
   # verify time and fname or time stamp in file
   time_ = datetime.now()
   fh = Dataset(fname,mode='r')
   n_level = fh.dimensions['lev'].size    
   n_lat = fh.dimensions['lat'].size
   n_lon = fh.dimensions['lon'].size
   dlat = 180.0/n_lat
   dlon = 360.0/n_lon
  
   Is =((np.array(lats)+90.0 )/dlat).astype('int32')
   Js =((np.array(lons)+180.0)/dlon).astype('int32')
   variables =[]
   for i in range(len(var_list)):
      var_name =  var_list[i]
      var_in = fh.variables[var_name][:, :, :, :]
      var = np.ndarray(shape=(n_level, len(Is)))
      for k in range(len(Is)):
        var[:,k] = var_in[0,:,Is[k],Js[k]]
      var_dict[var_name] = (n_level, var, fh.variables[var_name].__dict__)
   print('\n')
   print("finish " +fname, datetime.now() - time_)

def write_variables(fname, start_time, var_dict, lats, lons, second_increase):

   fh = Dataset(fname, 'w', format='NETCDF4')
   index  = fh.createDimension('index', len(lats))
   val_ = next(iter(var_dict.values()))
   level = fh.createDimension('lev', val_[0])
   
   second_ = fh.createVariable('second_increase', np.float32, ('index',))
   second_[:] = second_increase[:]
   time_stamp = start_time.strftime('%s-%02d-%02d %02d:%02d:%02d'%(start_time.year, \
                start_time.month,start_time.day,start_time.hour, start_time.minute, start_time.second))
   second_.units = "seconds since " + time_stamp
   second_.long_name = " second_increment" ;
   
   lats_  = fh.createVariable('lat', np.float32, ('index',))
   lats_.long_name = "latitude" ;
   lats_.units = "degrees_north" ;
   lons_  = fh.createVariable('lon', np.float32, ('index',))
   lons_.long_name = "longitude" ;
   lons_.units = "degrees_east" ;

   for key, value in var_dict.items():
      value_ = fh.createVariable(key, np.float32, ('lev','index',))
      value_.setncatts(value[2])
      value_[:,:] = value[1][:,:]
      
   lats_[:] =lats[:]
   lons_[:] =lons[:]

   fh.close()
   
   
if __name__ == '__main__' :
 
   # load input yaml
   stream = open("input.yaml", 'r')
   config = yaml.full_load(stream)

   # driven by output
   start_time = datetime.fromisoformat(str(config['output']['start_time']))
   end_time   = datetime.fromisoformat(str(config['output']['end_time']))
   out_duration = timedelta(seconds = int(config['output']['duration']))
 
   sat_reference_time = get_reference_time(config['locations']['template'], start_time)
   sat_duration = get_duration(config['locations'], start_time)
   distance = (start_time - sat_reference_time)/sat_duration
   sat_time = sat_reference_time + int(distance) * sat_duration

   #get first satellite data file name
   start_sat_fname = get_file_name_from_tpl(config['locations']['template'], sat_time)

   lats = []
   lons = []
   second_increase = []
   last_line = ''
   with open(start_sat_fname, 'rb') as f:
     f.seek(-2, os.SEEK_END)
     while f.read(1) != b'\n':
        f.seek(-2, os.SEEK_CUR)
     last_line = f.readline().decode()
   fin = open(start_sat_fname,'r')
   for _ , line in enumerate(fin):
      data = line.split()
      YY =int(data[0])
      MM =int(data[1])
      DD =int(data[2])
      HH =int(data[3])
      M  =int(data[4])
      SS =int(data[5])
      time  = datetime(YY, MM, DD, HH, M, SS)
      dtime = time - start_time 
      # get to the line
      if (time < start_time):
         continue
      # break if time passes the end time
      if (time  > end_time):
         break
      # start to read fields and write
      if (dtime == out_duration or line == last_line) :

         if (line == last_line) :
            second_increase.append(dtime.total_seconds())
            lats.append(float(str(data[6][0:])))
            lons.append(float(str(data[7][0:])))

         manager = mp.Manager()
         var_dict = manager.dict()
         model_fields = config['input_fields']
         # read variables 
         processes = []
         for fields in model_fields :
           for var_names, collection in fields.items():
              collection_ = config['collections'][collection['collection']]
              ftpl  = collection_['template']
              model_reference_time = get_reference_time(ftpl, start_time)
              model_frequency = get_duration(collection_, start_time)
              # by default, find the nearest model file
              distance   = (start_time - model_reference_time)/model_frequency 
              model_time = model_reference_time + int(distance) * model_frequency
              model_fname = get_file_name_from_tpl(ftpl, model_time)
              var_list = var_names.split()
              print('Reading file ' + model_fname, var_list)
              process = mp.Process(target = read_variables_para,  \
                                   args=(model_fname, model_time, var_list, lats, lons, var_dict))
              processes.append(process)
              process.start()

         for process in processes :
           process.join()

         # write out variables
         out_fname = get_file_name_from_tpl(config['output']['template'], start_time)
         write_variables(out_fname, start_time, var_dict, lats,lons, second_increase)
         var_dict.clear()
         lats.clear()
         lons.clear()
         second_increase.clear()
         start_time = start_time + out_duration
         dtime = timedelta(seconds = 0)
      
      second_increase.append(dtime.total_seconds())
      lats.append(float(str(data[6][0:])))
      lons.append(float(str(data[7][0:])))
   fin.close()
