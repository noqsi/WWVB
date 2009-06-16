/*
 * $Id$
 */

#include "stdlib.h"
#include "comedilib.h"

/*
The scheme here is to use an 80 kHz sample rate, mix with an aliased 60kHz local oscillator,
both I and Q phases, producing a complex baseband signal. Decimate by averaging 8 samples to make a bin.
The resulting decimated signal has a 10 kHz bandwidth, generously oversampled compared
to the ~1 kHz RF bandwidth. The 4/3 ratio of sample to LO frequency makes the sampled
LO signal +-1 or 0, so no multiplications are needed. An integral number of cycles per
bin makes the response of the decimation filter to aliased DC zero, suppressing
bias and flicker noise from the ADC.
*/


#define SIGNAL_HZ	60000
#define CYCLES_PER_BIN	6
#define SAMPLES_PER_BIN	8
#define BINS_PER_BUFFER 1250
#define SAMPLES_PER_BUFFER (SAMPLES_PER_BIN * BINS_PER_BUFFER)
#define SAMPLE_HZ	(SAMPLES_PER_BIN * SIGNAL_HZ / CYCLES_PER_BIN)
#define SAMPLE_NS	(1000000000 / SAMPLE_HZ)
#define SUMSHIFT	2	/* divide sum by 4 */
#define LOG_PERIOD	300	/* seconds */
#define LOG_BUFFERS	((SAMPLE_HZ/SAMPLES_PER_BUFFER)*LOG_PERIOD)

/*
 * DAQ_Cmd() creates the Comedi command to read channel 0.
 * Returns a pointer to a statically allocated command structure.
 */

comedi_cmd * DAQ_Cmd( void )
{
	static comedi_cmd c;
	
	// Range 3 is +-1.25V on the PCI-DAS1602/16
	static unsigned chan[1];
	chan[0] = CR_PACK( 0, 3, AREF_DIFF );

	c.subdev = 0;			// 0 is analog input
	c.flags = 0;			// not asking for special behavior
	
	c.start_src = TRIG_NOW;		// start
	c.start_arg = 0;		// without delay
	
	c.scan_begin_src = TRIG_FOLLOW;	// No scan delay
	c.scan_begin_arg = 0;		// 

	c.convert_src = TRIG_TIMER;	// Nyquist samples
	c.convert_arg = SAMPLE_NS;	// 125000 ns -> 80 kHz
	
	c.scan_end_src = TRIG_COUNT;	// a scan is just
	c.scan_end_arg = 1;		// a single sample.
	
	c.stop_src = TRIG_NONE;		// take data
	c.stop_arg = 0;			// indefinitely
	
	c.chanlist = chan;
	c.chanlist_len = 1;		// One channel
	
	return &c;
}

static void print_cmd( comedi_cmd *c )
{
	fprintf( stderr, "subdev:\t%d\n", c->subdev );
	fprintf( stderr, "flags:\t%d\n", c->flags );
	fprintf( stderr, "start_src:\t%d\n", c->start_src );
	fprintf( stderr, "start_arg:\t%d\n", c->start_arg );
	fprintf( stderr, "scan_begin_src:\t%d\n", c->scan_begin_src );
	fprintf( stderr, "scan_begin_arg:\t%d\n", c->scan_begin_arg );
	fprintf( stderr, "convert_src:\t%d\n", c->convert_src );
	fprintf( stderr, "convert_arg:\t%d\n", c->convert_arg );
	fprintf( stderr, "scan_end_src:\t%d\n", c->scan_end_src );
	fprintf( stderr, "scan_end_arg:\t%d\n", c->scan_end_arg );
	fprintf( stderr, "stop_src:\t%d\n", c->stop_src );
	fprintf( stderr, "stop_arg:\t%d\n", c->stop_arg );
}


void mix_decimate( sampl_t *in, short *out, int n )
{
	int i;

	for( i = 0; i < n; i+=1 ) {
		int aci = (int)*in++;
		int acq = -(int)*in++;
		aci -= *in++;
		acq += *in++;
		aci += *in++;
		acq -= *in++;
		aci -= *in++;
		acq += *in++;
		*out++ = aci >> SUMSHIFT;
		*out++ = acq >> SUMSHIFT;
	}
}

/*
 * Fill buffer. Handle partial reads, errors.
 */

void fill( int in, sampl_t *ib, int n )
{
	int nr, total = 0;

	while( total < n ) {
		nr = read( in, ib + total, (n - total) * sizeof( sampl_t) );
		if( nr < 0 ) {
			perror( "Reading from DAQ" );
			exit( 1 );
		}
		if( nr == 0 ) {
			fprintf( stderr, "Unexpected EOF from DAQ.\n" );
			exit( 1 );
		}
                if( nr % sizeof( sampl_t ) ) {
                        fprintf( stderr, "Odd count from DAQ\n" );
                        exit( 1 );
                }
		total += nr / sizeof( sampl_t);
	}
}

void log_time( void )
{
	static unsigned bc = 0;

	if( bc % LOG_BUFFERS == 0 ) {
		struct timeval tv;
		(void) gettimeofday( &tv, 0);
		fprintf( stderr, "%u\t%u\t%u\n", bc, tv.tv_sec, tv.tv_usec);
	}

	bc += 1;
}
	

/*
 * Get samples, decimate, write out
 */
 
void ferry( int in, int out )
{
	sampl_t ib[SAMPLES_PER_BUFFER];
	short ob[2*BINS_PER_BUFFER];
	
	for( ;; ) {
		fill( in, ib, SAMPLES_PER_BUFFER );
		mix_decimate( ib, ob, BINS_PER_BUFFER );
		log_time();
		/* write( out, ob, sizeof ob ); */
	}
}

int main(int argc,char *argv[])
{
	comedi_t *it;
	comedi_cmd *cmd;
	int err;
	
  	it=comedi_open("/dev/comedi0");
	if( it == NULL ) {
		perror( "/dev/comedi0" );
		exit( 1 );
	}

	cmd = DAQ_Cmd();
	print_cmd( cmd );
	if( err = comedi_command_test (it, cmd)) {
		comedi_perror( "comedi_command_test failed" );
		fprintf( stderr, "comedi_command_test returned %d\n", err);
		print_cmd( cmd );
		exit(1);
	}

	if ((err = comedi_command(it, cmd)) < 0) {
    		comedi_perror("comedi_command");
    		exit(1);
  	}
	
	ferry( comedi_fileno( it ), 1 );

}

/*
 * $Log$
 * Revision 1.2  2009-06-16 00:02:18  jpd
 * Timing test.
 *
 * Revision 1.1  2009-06-15 16:01:59  jpd
 * Initial checkin of WWVB project.
 *
 */
