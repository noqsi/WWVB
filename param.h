/* $Id$ */

/*
The scheme here is to use an 80 kHz sample rate, mix with an aliased 60kHz local
oscillator, both I and Q phases, producing a complex baseband signal. Decimate
by averaging 8 samples to make a bin. The resulting decimated signal has a 10
kHz bandwidth, generously oversampled compared to the ~1 kHz RF bandwidth. The
4/3 ratio of sample to LO frequency makes the sampled LO signal +-1 or 0, so no
multiplications are needed. An integral number of cycles per bin makes the
response of the decimation filter to aliased DC zero, suppressing bias and
flicker noise from the ADC.
*/


#define SIGNAL_HZ	60000
#define CYCLES_PER_BIN	6
#define BIN_HZ		(SIGNAL_HZ/CYCLES_PER_BIN)
#define SAMPLES_PER_BIN	8
#define BINS_PER_BUFFER 1250
#define BUFFER_HZ	(BIN_HZ/BINS_PER_BUFFER)
#define SAMPLES_PER_BUFFER (SAMPLES_PER_BIN * BINS_PER_BUFFER)
#define SAMPLE_HZ	(SAMPLES_PER_BIN * SIGNAL_HZ / CYCLES_PER_BIN)
#define SAMPLE_NS	(1000000000 / SAMPLE_HZ)
#define SUMSHIFT	2	/* divide sum by 4 */

/*
Latitude and longitude of WWVB, for scheduling DAQ and determining visibilities
of bursts and other astronomical objects. Should perhaps use midpoint between
WWVB and receving station, but this is close enough in practice.
 */
 
#define LONGITUDE (-105.02)	/* Degrees east */
#define LATITUDE (40.66)	/* Degrees north */
#define SECONDS_EAST ((int)(86400*(LONGITUDE/360.)))

/*
 * $Log$
 * Revision 1.2  2010-03-29 19:03:12  jpd
 * Coherently decimate to 1 Hz on the fly.
 *
 * Revision 1.1  2009-06-21 22:04:57  jpd
 * Share parameters.
 * Tuneup filter.
 *
 */
