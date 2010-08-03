/*
 * $Id$
 */

#include <unistd.h>
#include <stdlib.h>
#include <time.h> 
#include <sys/time.h>

#include <sched.h>
#include <sys/mman.h>
#include <string.h>

#include "comedilib.h"
#include "param.h"

#define LOG_PERIOD	300	/* seconds */
#define LOG_BUFFERS	((SAMPLE_HZ/SAMPLES_PER_BUFFER)*LOG_PERIOD)

/*
 * On a 32 bit machine, the downstream processing has trouble using
 * map mode I/O on a file more than 2^31 bytes long.
 */

#define MAXFILE (((unsigned)1)<<31)

/*
 * DAQ_Cmd() creates the Comedi command to read channel 0.
 * Returns a pointer to a statically allocated command structure.
 */

comedi_cmd * DAQ_Cmd( void )
{
	static comedi_cmd c;
	
	// Range 3 is +-1.25V on the PCI-DAS1602/16
	static unsigned chan[1];
	chan[0] = CR_PACK( 0, 3, AREF_GROUND );

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


void mix_decimate( sampl_t *in, float *out, int n )
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
		*out++ = aci ; /* >> SUMSHIFT; */
		*out++ = acq ; /* >> SUMSHIFT; */
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
		fprintf( stderr, "%u\t%u\t%u\n", bc, 
			(unsigned) tv.tv_sec, (unsigned) tv.tv_usec);
	}

	bc += 1;
}
	

/*
 * Get samples, decimate, write out
 */
 
void ferry( int in, int out )
{
	sampl_t ib[SAMPLES_PER_BUFFER];
	float ob[2*BINS_PER_BUFFER];
//	time_t now, tomorrow_noon;
//	int today;
//	int buffers;		/* buffers to output */
	int i;
	
//	now = time( NULL ) + SECONDS_EAST;	/* local solar time */
//	today = now/86400;
//	tomorrow_noon = 86400 * (today + 1) + 86400/2;
//	buffers = (tomorrow_noon - now) * BUFFER_HZ;

//	buffers = MAXFILE / sizeof( ob );
	
	/* Output forever */
	while(1){
		fill( in, ib, SAMPLES_PER_BUFFER );
		mix_decimate( ib, ob, BINS_PER_BUFFER );
		/* log_time(); */
		write( out, ob, sizeof ob );
	}
}

/* 
 * Real Time Support
 */

#define MY_PRIORITY (70) /* MAX priority is 80
                            Priority of kernel tasklets
                            and interrupt handler is 50 */

#define MAX_SAFE_STACK (512*1024) /* The maximum stack size which is
                                     guranteed safe to access without
                                     faulting (use 0.5MB, which is
                                     more than needed) */

void stack_prefault(void) {

        unsigned char dummy[MAX_SAFE_STACK];

        memset(&dummy, 0, MAX_SAFE_STACK);
        return;
}


int main(int argc,char *argv[])
{
	comedi_t *it;
	comedi_cmd *cmd;
	int err;
        struct sched_param param;

        /* Declare ourself as a real time task */

        param.sched_priority = MY_PRIORITY;
        if(sched_setscheduler(0, SCHED_FIFO, &param) == -1) {
                perror("sched_setscheduler failed");
                exit(-1);
        }

        /* Lock memory */

        if(mlockall(MCL_CURRENT|MCL_FUTURE) == -1) {
                perror("mlockall failed");
                exit(-2);
        }

        /* Pre-fault our stack */

        stack_prefault();

        /* COMEDI/Data Acquisition Loop */

  	it=comedi_open("/dev/comedi0");
	if( it == NULL ) {
		perror( "/dev/comedi0" );
		exit( 1 );
	}

	cmd = DAQ_Cmd();
	print_cmd( cmd );
	if( (err = comedi_command_test (it, cmd))) {
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
	exit(0);

}

/*
 * $Log$
 * Revision 1.8  2010-08-03 14:54:55  jpd
 * Added Matt's revisions:
 * - Data acquisition code in wwvbaq.c now uses real time priority; Makefile hacked accordingly
 *
 * - wwvbred.py no longer uses memmap; wwvbred now reads single lines of data
 *   off of a bitstream piped to it from wwvbaq. The scrupt wwvbaq.sh is now pipelined
 *
 * - wwvbred.py reads the time off of the signal piped to it to it using the
 *   codes described here: http://en.wikipedia.org/wiki/WWVB#Time_Code_Format
 *   - Initially, wwvbred throws data into a buffer until it detects the time,
 *     then opens a file wwvb-YYYYMMDDhhmmss-epoch.tsv where "epoch" is the number
 *     of seconds since midnight January 1, 1970
 *   - Every day at midnight UTC, wwvbred.py changes to outputting to a new file
 *
 * - wwvbred.py corrects for the 45 degree phase shift that happens between 10
 *   and 15 minutes on the hour, as documented here:
 *   http://en.wikipedia.org/wiki/WWVB#Station_ID
 *
 * - wwvbaq_rename.py renames legacy datafiles using the same logic and conventions from in wwvbred.py
 *
 * - Created directory "fermi":
 *   - proc_fermi_grbs.sh is a toplevel script that does the following:
 *     - Grabs http://gcn.gsfc.nasa.gov/fermi_grbs.html with curl
 *     - pipes that to parse_fermi_grbs.awk
 *     - optionally pipes that to find_fermi_events.py (currently disabled)
 *   - parse_fermi_grbs.awk generates an XEphem database of fermi gamma-ray burst events
 *   - find_fermi_events.py reads the database generated by parse fermi grbs, uses the local
 *     latitude and longitude of Noqsi aerospace (40.00953472, -105.20454705)
 *     and calculates whether the event was above the local horizon using PyEphem
 *
 * Revision 1.7  2010-07-25 16:32:39  jpd
 * First real production versions.
 *
 * Revision 1.6  2010-03-29 20:01:26  jpd
 * Further fixes for coherent decimation.
 *
 * Revision 1.5  2010-03-29 19:03:12  jpd
 * Coherently decimate to 1 Hz on the fly.
 *
 * Revision 1.4  2009-06-22 00:35:38  jpd
 * First light.
 *
 * Revision 1.3  2009-06-21 22:04:57  jpd
 * Share parameters.
 * Tuneup filter.
 *
 * Revision 1.2  2009-06-16 00:02:18  jpd
 * Timing test.
 *
 * Revision 1.1  2009-06-15 16:01:59  jpd
 * Initial checkin of WWVB project.
 *
 */
