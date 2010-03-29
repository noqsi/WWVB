import posix
import numpy
import pylab

BIN_HZ = 10000
BIN_BYTES = 8
BIN_DTYPE = numpy.complex64

binfile = sys.stdin

def bytecount( f ):
	return posix.stat( f )[6]


# Template for bit sync: approximates the average power in the signal
# over a one second bit time. m is the sample frequency.

def template( m ):
	t = numpy.zeros( m )
	for i in range( m/5, m/2 ): t[i] = 0.53
	for i in range( m/2, (4*m)/5 ): t[i] = 0.88
	for i in range( (4*m)/5, m ): t[i] = 1.0
	return t

# Fourier transform of bit sync template for fast cross correlation.

def fourplate( m ):
	return numpy.conjugate( numpy.fft.rfft( template( m )))

# Fold sum of absolute values of array d into an array of length n.

def folda( d, n ):
	return numpy.sum(numpy.absolute(numpy.reshape(d,(-1,n))), axis=0)

# Map in secs of data from offset off within data file.
# Units for secs and off are seconds.

def locate_data( off, secs ):
	return numpy.memmap( binfile, dtype=BIN_DTYPE, mode="r", offset = BIN_HZ * BIN_BYTES * off, shape = BIN_HZ * secs )

# Fold modulo one second.

def fold1( off, secs ):
	return folda( locate_data( off, secs ), BIN_HZ )

# Template cross correlation with bit sync.

def tcc1( off, secs ):
	return numpy.fft.irfft( fourplate( BIN_HZ ) * numpy.fft.rfft( fold1( off, secs )))

# The location of the cross correlation peak is the delay in samples
# of the first bit in the array.

def bitdelay( off, secs ):
	return numpy.argmax( tcc1( off, secs ))

# find the first bit in the file, we'll need it.

firstbit = bitdelay( 0, 200 )

# correct FFT bin number to negative if necessary.

def modfreq( bins, secs ):
	if( bins > secs*BIN_HZ/2 ):
		return bins - secs * BIN_HZ
	return bins

# Find the carrier frequency offset in HZ

def freqoff( off, secs ):
	return modfreq( numpy.argmax(numpy.absolute(numpy.fft.fft(locate_data(off,secs)))), secs ) / float( secs )

basefreq = freqoff(0,200)/BIN_HZ

# Create an array containing a complex wave with frequncy f per step

def esig( f, n ):
	return numpy.power( numpy.exp( 2j*numpy.pi*f ), numpy.arange( n ))

# phase correction function for one second.

pcorr = esig( -basefreq, BIN_HZ )

def sumslice( s, a, b ):
	return numpy.average( s[ BIN_HZ * a / 10 : BIN_HZ * b / 10] )

def slices( s ):
	return (
		sumslice( s, 0, 2 ),
		sumslice( s, 2, 5 ),
		sumslice( s, 5, 8 ),
		sumslice( s, 8, 10 ))

def locate_bit( off ):
	return numpy.memmap( binfile, dtype=BIN_DTYPE, mode="r", offset = BIN_BYTES * off, shape = BIN_HZ )

def classify_bit( slc ):
	sa = numpy.absolute( slc )
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
	sa = numpy.absolute( slc )
	t = ( sa[0] + sa[3] ) / 2		# threshold
	s0 = numpy.absolute( s[0] )
	s1 = numpy.absolute( s[1] )
	o = ( t - s0 )/( s1 - s0 )		# linear
	if( o < -0.5 ): return -1
	if( o > 0.5 ): return 1
	return 0

def detrend( a ):
	n = len( a )
	return a - a[0] + ( a[0] - a[n-1] ) / n * numpy.arange( n )

def hipass( a ):
	af = numpy.fft.rfft(a)
	af[0:int(len(a)/100)] = 0
	return numpy.fft.irfft(af)

def measure_bits():
	# Overestimate the number of seconds of data we have.
	# We won't know exactly until we process it, but a slight
	# overestimate allows us to create arrays for the reduced
	# data without serious waste. Slice 'em when done.
	seconds = int( 1.001 * bytecount( binfile ) / BIN_HZ / BIN_BYTES )
	amplitude = numpy.zeros( seconds, dtype = numpy.complex64 )
	bit = numpy.zeros( seconds, dtype = numpy.int )
	bitoff = numpy.zeros( seconds, dtype = numpy.int )
	thisbit = firstbit
	for i in range( seconds ):
		try: signal = pcorr * locate_bit( thisbit)
		except:
			return ( numpy.absolute(amplitude[:i]),
				detrend(numpy.unwrap(numpy.angle(amplitude[:i]))),
				bit[:i],
				bitoff[:i] )
		bitoff[i] = thisbit
		chunks = slices( signal )
		bit[i] = classify_bit( chunks )
		amplitude[i] = numpy.exp( -2j*numpy.pi*basefreq*thisbit ) * sumbit( chunks, bit[i] )
		thisbit += BIN_HZ + startoff( signal, chunks )

a, p, b, o = measure_bits()

# Make a TSV file containing 1 second sampled data
# Fields are:
#	Start of bit in bins
#	Phase in radians
#	Amplitude (arbitrary units)
#	Demodulated time code symbol (0,1 are bits, 2 is a marker)

for i in range(len(a)):
	print "%d\t%g\t%g\t%d" % (o[i],p[i],a[i],b[i])


