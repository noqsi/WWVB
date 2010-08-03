#!/usr/bin/env python

import numpy as np
import sys
import time
import calendar

BIN_HZ = 10000
BIN_BYTES = 8
BIN_DTYPE = np.complex64
BGN_SECS = 200

# Template for bit sync: approximates the average power in the signal
# over a one second bit time. m is the sample frequency.

def template( m ):
	t = np.zeros( m )
	for i in range( m/5, m/2 ): t[i] = 0.53
	for i in range( m/2, (4*m)/5 ): t[i] = 0.88
	for i in range( (4*m)/5, m ): t[i] = 1.0
	return t

# Fourier transform of bit sync template for fast cross correlation.

def fourplate( m ):
	return np.conjugate( np.fft.rfft( template( m )))

# Get secs of data using offset from sys.stdin 
# Units for secs and off are seconds.
# We may also hand an optional array old_data for use with offset, 
# old_data defaults to an empty array if not specified

def locate_data( off, secs, old_data=np.array([], dtype=BIN_DTYPE)):
	if (off == 0):
		return np.fromfile(file=sys.stdin, dtype=BIN_DTYPE, count=BIN_HZ * secs)
	elif (off > 0):
		np.fromfile(file=sys.stdin, dtype=BIN_DTYPE, count=off)
		return np.fromfile(file=sys.stdin, dtype=BIN_DTYPE, count=BIN_HZ * secs)
	elif (off < 0):
		return np.append(
		         np.resize(np.roll(old_data,abs(off)), abs(off)),
		         np.fromfile(file=sys.stdin, dtype=BIN_DTYPE, count=(BIN_HZ * secs) + off)
                       )

# Fold sum of absolute values of array data into an array of length n.

def folda( data, n ):
	return np.sum(np.absolute(np.reshape(data,(-1,n))), axis=0)

# Fold modulo one second
def fold1 ( data ):
	return folda(data, BIN_HZ)

# Template cross correlation with bit sync.

def tcc1( data ):
	return np.fft.irfft( fourplate( BIN_HZ ) * np.fft.rfft( fold1( data )))

# The location of the cross correlation peak is the delay in samples
# of the first bit in the array.

def bitdelay( data ):
	return np.argmax( tcc1( data ))

# find the offset of the first bit, we'll need it.

print >>sys.stderr, "Gathering first %i seconds of data" % BGN_SECS
first_secs = locate_data( 0, BGN_SECS )
firstbit = bitdelay( first_secs )
print >>sys.stderr, "Initial offset is %i um" % firstbit

# correct FFT bin number to negative if necessary.

def modfreq( bins, secs ):
	if( bins > secs*BIN_HZ/2 ): return bins - secs * BIN_HZ
	else: return bins

# Find the carrier frequency offset in HZ

def freqoff( data, secs):
	return modfreq( np.argmax(np.absolute(np.fft.fft(data))), secs ) / float( secs )

basefreq = freqoff(first_secs,BGN_SECS)/BIN_HZ
print >>sys.stderr, "Base frequency is %f Hz" % basefreq

# Create an array containing a complex wave with frequncy f per step

def esig( f, n ):
	return np.power( np.exp( 2j*np.pi*f ), np.arange( n ))

# phase correction function for one second.

pcorr = esig( -basefreq, BIN_HZ )
print >>sys.stderr, "The phase correction for one second is", pcorr

def sumslice( s, a, b ):
	return np.average( s[ BIN_HZ * a / 10 : BIN_HZ * b / 10] )

def slices( s ):
	return (
		sumslice( s, 0, 2 ),
		sumslice( s, 2, 5 ),
		sumslice( s, 5, 8 ),
		sumslice( s, 8, 10 ))

def classify_bit( slc ):
	sa = np.absolute( slc )
	t = ( sa[0] + sa[3] ) / 2		# threshold
	if( sa[2] < t ): return 2		# marker
	if( sa[1] < t ): return 1
	return 0


def sumbit( slc, cls ):
	if( cls == 0 ):
		return 0.375 * ( slc[1] + slc[2] ) + 0.25 * slc[3]
	if( cls == 1 ):
		return 0.6 * slc[2] + 0.4 * slc[ 3 ]
	return slc[3]


def startoff( s, slc ):
	sa = np.absolute( slc )
	t = ( sa[0] + sa[3] ) / 2		# threshold
	s0 = np.absolute( s[0] )
	s1 = np.absolute( s[1] )
	o = ( t - s0 )/( s1 - s0 )		# linear
	if( o < -0.5 ): return -1
	if( o > 0.5 ): return 1
	return 0

def hipass( a ):
	af = np.fft.rfft(a)
	af[0:int(len(a)/100)] = 0
	return np.fft.irfft(af)

# Main Loop
# Make a TSV file containing 1 second sampled data
# Fields are:
#	Start of bit in bins
#	Phase in radians
#	Amplitude (arbitrary units)
#	Demodulated time code symbol (0,1 are bits, 2 is a marker)
#
# Autodetect time from incoming data correct
# Correct for when phase winds around
# Correct for phase adjustment in signal occurring between minutes 10 through 15

def main():
	signal = locate_data(firstbit,1)
        bitoff = BGN_SECS * BIN_HZ + firstbit
	time = False
	queue = []
	winds = 0
	phase = False
	while True:
		# gather data from the signal
		chunks = slices( pcorr * signal )
		bit = classify_bit( chunks )
		measurement = np.exp( -2j*np.pi*basefreq*bitoff ) * sumbit( chunks, bit )
		oldphase = phase
		amplitude = np.absolute(measurement)
		phase = np.angle(measurement)

		# If the phase changed by a large amount, adjust the number of windings
		if (abs(phase - oldphase) > np.pi): winds += np.sign(oldphase - phase)

		# enqueue in the output stream
                queue.append((bitoff, phase, amplitude, bit, winds))

		# If we don't know the time, try to infer it from the data queue
                if time == False:
			i = 0
			while (i < len(queue)-59 and time == False):
				time = get_time(queue,i)
				i += 1
			if time != False:
				print >>sys.stderr, "Directing file output to:", filename(time,i-1)
				f = open(filename(time,i-1), 'w')
				for j in range(i):
					print_data(f, queue.pop(0), time, i-j-1)
		else: 
			# If we do know the time...
			# first check to see if there's a new time from the queue
			newtime = get_time(queue,0)
			if (newtime != False): 
				time = newtime
				# If we are at midnight, change the file output to a new day
				if (time[2] == 0 and time[3] == 0):
					f.close()
					print >>sys.stderr, "Directing file output to:", filename(time,0)
					f = open(filename(time,0), 'w')
			# Then output the top of the queue to file
			print_data(f, queue.pop(0), time, 0)
				
		# Finally, update the signal for the next round
                signal = locate_data(startoff( signal, chunks ), 1, signal)
                bitoff = bitoff + BIN_HZ + startoff( signal, chunks ) 

# Grab the time from an array containing part of the WWVB bitstream
def get_time(queue,i):
	if ( i + 60 > len(queue) or
	     not(queue[i][3]    == 2 and \
                 queue[i+9][3]  == 2 and \
                 queue[i+19][3] == 2 and \
                 queue[i+29][3] == 2 and \
                 queue[i+39][3] == 2 and \
                 queue[i+49][3] == 2 and \
                 queue[i+59][3] == 2      )): return False
	else:
		# Decode the time from the stream
		# Minutes
		minutes = (queue[i+1][3]*4 + queue[i+2][3]*2 + queue[i+3][3])*10 + \
           		   queue[i+5][3]*8 + queue[i+6][3]*4 + queue[i+7][3]*2 + queue[i+8][3]

		# Hours
		hours = (queue[i+12][3]*2 + queue[i+13][3])*10 + \
         		 queue[i+15][3]*8 + queue[i+16][3]*4 + queue[i+17][3]*2 + queue[i+18][3]

		# Day of year
		doy = (queue[i+22][3]*2 + queue[i+23][3])*100 + \
      		      (queue[i+25][3]*8 + queue[i+26][3]*4 + queue[i+27][3]*2 + queue[i+28][3])*10 + \
       		       queue[i+30][3]*8 + queue[i+31][3]*4 + queue[i+32][3]*2 + queue[i+33][3]

		# Year
		year = (queue[i+45][3]*8 + queue[i+46][3]*4 + queue[i+47][3]*2 + queue[i+48][3])*10 + \
		        queue[i+50][3]*8 + queue[i+51][3]*4 + queue[i+52][3]*2 + queue[i+53][3]

		# Return tuple in conventional astronomical ordering
		return (year, doy, hours, minutes)

def print_data (f, (bitoff, phase, amplitude, bit, winds), 
                   (ys, doy, hs, ms), secs_correction):
	if secs_correction != 0:
		# Turns WWVB time to a time structure from the time module
		t = time.strptime("%02d %03d %02d:%02d:00" % (ys, doy, hs, ms),
               		          "%y %j %H:%M:%S")
		# Turns the time time to POSIX time applying the seconds correction
		pt = calendar.timegm(t) - secs_correction
		# Grab the new time structure with adjusted time
		nt = time.gmtime(pt)
		ms = nt.tm_min

	# We need to adjust the phase because the WWVB signal has a slight phase shift
	if (ms >= 10 and ms < 15): winds += 0.25

	print >>sys.stderr, "%d\t%g\t%g\t%d" % (bitoff, phase + 2*np.pi*winds, amplitude, bit)
	print >>f, "%d\t%g\t%g\t%d" % (bitoff, phase + 2*np.pi*winds, amplitude, bit)
	f.flush()

# Generate a filename from a WWVB time-tuple
def filename(wwvbtime,secs_correction):
	t = time.strptime("%02d %03d %02d:%02d:00" % wwvbtime, \
                          "%y %j %H:%M:%S")
	pt = calendar.timegm(t) - secs_correction
	# Turns the time time to astronomer format
	YmdHMS = time.strftime("%Y%m%d%H%M%S",time.gmtime(pt))
	return "./Data/wwvbaq-%s_%d.tsv" % (YmdHMS, pt)

# Main loop
main()
