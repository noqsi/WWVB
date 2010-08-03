#!/usr/bin/env python

# This program returns a correct WWVBAQ tsv file name
# The correct format is
# "wwvbaq-YYYYMMDDhhmmss_posix.tsv"
# where 
# # YYYYMMDDhhmmss is the year/month/day/hour/minute/second
# # posix is the time in seconds since midnight 1970/1/1

# The naming convention for a WWVBAQ file is "wwvbaq-tttttt.tsv"
# where 'tttttt' is seconds from 00:00:00 UTC 1/1/1970 (POSIX time)

# Since the signal from the WWVB antenna contains a time signature,
# the correct time stamp may be infered from the contents of the file
# We use the WWVB codes presented in the fourth column of a WWVBAQ tsv file
# Read http://en.wikipedia.org/wiki/WWVB#Time_Code_Format for details

import sys
import re
import time
import calendar

# FIXME: make error checks more rigorous
Usage = "Usage: mv wwvbaq-XXXX.tsv `%s wwvbaq-XXXX.tsv`" % sys.argv[0]

if len(sys.argv) != 2:
   print >> sys.stderr, Usage
   sys.exit(2)

if re.match(r"^wwvbaq-.+.tsv$",sys.argv[1]) == None:  
   print >> sys.stderr, sys.argv[1], 'is not a WWVBAQ tsv file'
   print >> sys.stderr, Usage
   sys.exit(2)

file = open(sys.argv[1])

def wwvb_code(line):
    """wwvb_code(string) -> int

Remove the trailing \\ns and split at the \\ts,
after splitting, grab the fourth element 
and coerce it into an int.
These are the WWVB codes"""
    return int(line.rstrip().split("\t")[3])

ls = map(wwvb_code,file.readlines())
file.close()

# We now decode the WWVB protocol
# Read http://en.wikipedia.org/wiki/WWVB#Time_Code_Format for details

# Keep skipping until we find the start of a correctly formatted minute
i = 0
while (not(ls[i]    == 2 and \
           ls[i+9]  == 2 and \
           ls[i+19] == 2 and \
           ls[i+29] == 2 and \
           ls[i+39] == 2 and \
           ls[i+49] == 2 and \
           ls[i+59] == 2      )): i += 1

# Minutes
minutes = (ls[i+1]*4 + ls[i+2]*2 + ls[i+3])*10 + \
           ls[i+5]*8 + ls[i+6]*4 + ls[i+7]*2 + ls[i+8]

# Hours
hours = (ls[i+12]*2 + ls[i+13])*10 + \
         ls[i+15]*8 + ls[i+16]*4 + ls[i+17]*2 + ls[i+18]

# Day of year
doy = (ls[i+22]*2 + ls[i+23])*100 + \
      (ls[i+25]*8 + ls[i+26]*4 + ls[i+27]*2 + ls[i+28])*10 + \
       ls[i+30]*8 + ls[i+31]*4 + ls[i+32]*2 + ls[i+33]

# Year
year = (ls[i+45]*8 + ls[i+46]*4 + ls[i+47]*2 + ls[i+48])*10 + \
        ls[i+50]*8 + ls[i+51]*4 + ls[i+52]*2 + ls[i+53]

# Create a string with this data, and then us time.strptime to make a time_struct
t = time.strptime("%02d:%02d:00 %03d %02d" % (hours,minutes,doy,year), \
                  "%H:%M:%S %j %y")

# Call calendar.timegm() to turn t into POSIX time, corrected for the seconds i
pt = calendar.timegm(t) - i

# Convert epoch time to human readable time
YmdHMS = time.strftime("%Y%m%d%H%M%S",time.gmtime(pt))
print "wwvbaq-%s_%d.tsv" % (YmdHMS, pt)
#print "%d:%d %d %d" % (hours, min, doy, year)
#print time.mktime([year, -1, -1, hours, minutes, 0, -1, doy, -1])
