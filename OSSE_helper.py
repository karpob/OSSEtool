#!/usr/bin/env python

import math
import numpy as np
from netCDF4 import Dataset
from datetime import datetime
from datetime import timedelta
import glob

# given a template with {y4} {m2} {d2} {h2} {mn2} and {s2}
def get_filename_from_tpl(ftpl, time) :
  return ftpl.format(y4=time.year, m2=str(time.month).zfill(2), \
                  d2 = str(time.day).zfill(2), h2=str(time.hour).zfill(2), \
                  mn2= str(time.minute).zfill(2), s2=str(time.second).zfill(2))

def get_time_from_filename(ftpl, filename):
  last_ = ftpl.rfind('/')
  fname = ftpl[last_+1:]
  k_year = fname.find('{y4}')
  k_mon  = fname.find('{m2}')
  k_day  = fname.find('{d2}') - 2
  k_hour = fname.find('{h2}') - 4
  k_min  = fname.find('{mn2}')- 6
  k_sec  = fname.find('{s2}') - 9

  last_ = filename.rfind('/')
  fname = filename[last_+1:]
  YYYY  = fname[k_year:k_year+4] if k_year >=0 else '0000'
  MM    = fname[k_mon:k_mon+2]   if k_mon  >=0 else '00'
  DD    = fname[k_day:k_day+2]   if k_day  >=0 else '00'
  HH    = fname[k_hour:k_hour+2] if k_hour >=0 else '00'
  MN    = fname[k_min:k_min+2]   if k_min  >=0 else '00'
  SS    = fname[k_sec:k_sec+2]   if k_sec  >=0 else '00'

  time_format = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
  return datetime.fromisoformat(time_format)

def get_two_files_from_tpl(ftpl, time):
   last_ = ftpl.rfind('/')
   fpath = ftpl[:last_] if (last_ >=0) else '.'
   fpath = get_filename_from_tpl(fpath, time)

   fname = ftpl[last_+1:]
   wild  = fname.replace('{y4}','*').replace('{m2}','*').replace('{d2}','*').replace('{h2}','*').replace('{mn2}','*')
   files = glob.glob(fpath+'/'+wild) 
   files.sort()
   assert files, "cannot find files " + fpath+'/'+wild
   if len(files) == 1:
      files.append('')
   return files[0], files[1]

def get_reference_time(ftpl, time):
   file0, file1 = get_two_files_from_tpl(ftpl, time)
   return get_time_from_filename(ftpl, file0)

def get_duration(collection, time):
   ftpl = collection['template']
   file0, file1 = get_two_files_from_tpl(ftpl, time)
   # if only one file, need duration
   if not file1 : 
      assert 'duration' in collection, "duration is needed when there is only one file: " + file0
      return timedelta(seconds = int(collection['duration']))
   ref_time0 = get_time_from_filename(ftpl, file0)
   ref_time1 = get_time_from_filename(ftpl, file1)
   return  ref_time1-ref_time0

def get_pre_filename(collection, time):
   duration = get_duration(collection, time)
   ftpl = collection['template']
   ref_time = get_reference_time(ftpl, time)
   distance = math.floor((time -ref_time)/duration)
   time_ = ref_time + distance * duration
   return get_filename_from_tpl(ftpl, time_)

def get_post_filename(collection, time):
   duration = get_duration(collection, time)
   ftpl = collection['template']
   ref_time = get_reference_time(ftpl, time)
   distance = math.ceil((time -ref_time)/duration)
   time_ = ref_time + distance * duration
   return get_filename_from_tpl(ftpl, time_)

def get_file_numbers(collection, start_time, end_time):
   duration = get_duration(collection, start_time)
   first_file = get_pre_filename(collection, start_time)
   last_file  = get_pre_filename(collection, end_time)
   ftpl = collection['template']
   first_time = get_time_from_filename(ftpl, first_file)
   last_time = get_time_from_filename (ftpl, last_file)
   return int(1+(last_time - first_time)/duration) 

def read_sat_data(collection, start_time, end_time):
   #here collection is locations
   k = get_file_numbers(collection, start_time, end_time)
   duration = get_duration(collection, start_time)
   lats = []
   lons = []
   seconds_increase = []

   for i in range(k):
      # satellite tracks start 3 hours prior
      
      sat_fname = get_pre_filename(collection, start_time + timedelta(hours=3) + i*duration)
      print("\nReading satellite track data file "+sat_fname) 
      fin = open(sat_fname,'r')
      for j , line in enumerate(fin):
         data = line.split()
         YY =int(data[0])
         MM =int(data[1])
         DD =int(data[2])
         HH =int(data[3])
         M  =int(data[4])
         SS =int(data[5])
         time  = datetime(YY, MM, DD, HH, M, SS)
         if (time < start_time):
            continue
         if (time > end_time):
            break
         dtime = time - start_time
         seconds_increase.append(dtime.total_seconds())
         lats.append(float(str(data[6][0:])))
         lons.append(float(str(data[7][0:])))
      fin.close()
      return lats, lons, seconds_increase

def read_vars_from_collection(var_names, collection, start_time, end_time, lats, lons, seconds_increase,var_dict) :
   k = get_file_numbers(collection, start_time, end_time)
   duration = get_duration(collection, start_time)
   fname = get_pre_filename(collection, start_time)
   time_ = get_time_from_filename(collection['template'], fname)
   offset = (start_time - time_).total_seconds()
   
   fh = Dataset(fname,mode='r')
   if('lev' in fh.dimensions.keys()):
      n_level = fh.dimensions['lev'].size
   else:
      n_level = 1
   n_lat = fh.dimensions['lat'].size
   n_lon = fh.dimensions['lon'].size
   dlat = 180.0/n_lat
   dlon = 360.0/n_lon
   fh.close()

   var = np.ndarray(shape=(n_level, len(lats)))

   k0 = 0
   k1 = 0
   
   for i in range(k):
      while k1 < len(lats) :
         if (seconds_increase[k1] + offset >= (i+1) * duration.total_seconds()) :
            break
         k1 += 1
         
      # for each file, figure out the time that passed in
      fname = get_pre_filename(collection, time_)
      fh = Dataset(fname,mode='r')
      Is =((np.array(lats[k0:k1])+90.0 )/dlat).astype('int32')
      Js =((np.array(lons[k0:k1])+180.0)/dlon).astype('int32')
      var_list = var_names.split()
      vars_str = ' '.join([vname for vname in var_list])
      whir = ' start {} end {} time {}'.format(start_time,end_time,time_)
      print("\nReading (" + vars_str + ") from " + fname+whir) 
      for var_name in var_list:
        if(n_level>1):
          var_in = fh.variables[var_name][:, :, :, :]
        else:
          var_in = fh.variables[var_name][:,:,:]
        for ki in range(len(Is)):
          if(n_level>1):
            var[:,k0+ki] = var_in[0,:,Is[ki],Js[ki]]
          else:
            var[:,k0+ki] = var_in[0,Is[ki],Js[ki]]
            
      # this last file
      if (i == k-1) : 
         var_dict[var_name] = (n_level, var, fh.variables[var_name].__dict__)
      fh.close()
      k0 = k1
      time_  = time_ + duration

def write_variables(fname, start_time, var_dict, lats, lons, seconds_increase):

   fh = Dataset(fname, 'w', format='NETCDF4')
   index  = fh.createDimension('time', len(lats))
   val_ = next(iter(var_dict.values()))
   if(val_[0]>1):
      vv = val_[0]
   else:
      vv = 72
   level = fh.createDimension('lev', vv)
   levs = fh.createVariable('lev', np.int, ('lev',))
   levs[:] = np.arange(1,vv+1)

   ls_ = fh.createDimension('ls',19)

   second_ = fh.createVariable('time', np.float32, ('time',))
   second_[:] = seconds_increase[:]
   time_stamp = start_time.strftime('%s-%02d-%02d %02d:%02d:%02d'%(start_time.year, \
                start_time.month,start_time.day,start_time.hour, start_time.minute, start_time.second))
   second_.units = "seconds since " + time_stamp
   second_.long_name = " seconds_increment" ;
   tyme = []
   for sss in seconds_increase:
      tyme.append(start_time+timedelta(seconds=sss))
   
   isotime = fh.createVariable('isotime','S1',('time','ls'))
   isotime.long_name = 'Time (ISO Format)'
   isotmp = np.zeros((len(lons),19),dtype='S1')
   for i in range(len(lons)):
      isotmp[i][:] = list(tyme[i].isoformat())
   isotime[:] = isotmp[:]


   lats_  = fh.createVariable('trjLat', np.float32, ('time',))
   lats_.long_name = "latitude" ;
   lats_.units = "degrees_north" ;
   lons_  = fh.createVariable('trjLon', np.float32, ('time',))
   lons_.long_name = "longitude" ;
   lons_.units = "degrees_east" ;

   for key, value in var_dict.items():
      if(value[0]>1):
        value_ = fh.createVariable(key, np.float32, ('time','lev',))
        value_.setncatts(value[2])
        value_[:,:] = value[1][:,:].T
      else:
        value_ = fh.createVariable(key, np.float32, ('time',))
        value_.setncatts(value[2])
        value_[:] = value[1][0,:]
       

   lats_[:] =lats[:]
   lons_[:] =lons[:]

   fh.close()

if __name__ == '__main__' :

  ftmp = 'Year {y4} month {m2} day {d2} hour {h2} minute {mn2} second {s2}'
  now = datetime.now()
  name = get_filename_from_tpl(ftmp, now)
  print(name)

