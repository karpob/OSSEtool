#!/usr/bin/env python

from datetime import datetime
from datetime import timedelta
import glob

# given a template with {y4} {m2} {d2} {h2} {mn2} and {s2}
def get_file_name_from_tpl(ftpl, time) :
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
  return YYYY, MM, DD, HH, MN, SS

def get_two_files_from_tpl(ftpl, time):
   last_ = ftpl.rfind('/')
   fpath = ftpl[:last_] if (last_ >=0) else '.'
   fpath = get_file_name_from_tpl(fpath, time)

   fname = ftpl[last_+1:]
   wild  = fname.replace('{y4}','*').replace('{m2}','*').replace('{d2}','*').replace('{h2}','*').replace('{mn2}','*')
   files = glob.glob(fpath+'/'+wild)
   assert files, "cannot find files " + fpath+'/'+wild
   if len(files) == 1:
      files.append('')
   return files[0], files[1]

def get_reference_time(ftpl, time):
   file0, file1 = get_two_files_from_tpl(ftpl, time)
   YYYY, MM, DD, HH, MN, SS = get_time_from_filename(ftpl, file0)
   time_format = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
   ref_time = datetime.fromisoformat(time_format)
   return ref_time   

def get_duration(collection, time):
   ftpl = collection['template']
   file0, file1 = get_two_files_from_tpl(ftpl, time)
   # if only one file, need duration
   if not file1 : 
      assert 'duration' in collection, "duration is needed when there is only one file: " + file0
      duration = timedelta(seconds = int(collection['duration']))
      return duration
   YYYY, MM, DD, HH, MN, SS = get_time_from_filename(ftpl, file0)
   time_format = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
   ref_time0 = datetime.fromisoformat(time_format)
   YYYY, MM, DD, HH, MN, SS = get_time_from_filename(ftpl, file1)
   time_format = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
   ref_time1 = datetime.fromisoformat(time_format)
   duration = ref_time1-ref_time0
   return duration

if __name__ == '__main__' :

  ftmp = 'Year {y4} month {m2} day {d2} hour {h2} minute {mn2} second {s2}'
  now = datetime.now()
  name = get_file_name_from_tpl(ftmp, now)
  print(name)

