#!/usr/bin/env python

import sys
import ephem
import re
from math import pi

def ephem2unix(date):
    """Converts an ephem timestamp to a POSIX date (an int)"""
    return int(86400 * (date - ephem.date('1970/1/1')))

# Halfway between Noqsi Aerospace @ 2822 South Nova Rd, Pine, CO
# and the WWVB transmitter in Fort Collins
noqsi = ephem.Observer()
noqsi.lat, noqsi.long = '40.00953472222222', '-105.20454705555557'

while True:
    line1 = sys.stdin.readline()

    # Exit at eof
    if line1 == '': exit()

    # The next line ensures that:
    # # line1 contains commented fermi data
    # # line2 is an xephem database entry
    if re.match("#",line1) == None: continue

    error = float(re.search('(\d+.\d\d)\n$',line1).group(1))
    # if the error is greater than 10 degrees, throw away
    if error > 10: continue

    noqsi.date = re.search(r"..../../.. ..:..:......",line1).group()

    # if the date is before 2010/4/1, quit 
    # since we don't have measurements as early as that
    if noqsi.date < ephem.date('2010/4/1'):
        exit()

    line2 = sys.stdin.readline()

    entry = ephem.readdb(line2)
    entry.name = re.search(r"^..(\w+)",line1).group(1)
    entry.compute(noqsi)
    entry_alt_degrees = entry.alt/pi*180

    sun = ephem.Sun()
    sun.compute(noqsi)
    sun_alt_degrees = sun.alt/pi*180

    if 0 < entry.alt: # if the entry is above the horizon, print
       print "%s\t%s\t%f\t%d\t%f\t%f\t%f" % \
             (entry.name, noqsi.date, ephem.julian_date(noqsi),\
              ephem2unix(noqsi.date), sun_alt_degrees, entry_alt_degrees, error)
