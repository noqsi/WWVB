/* $Id$ */

#include <stdlib.h>
#include <stdio.h>
#include "param.h"

#define RESAMP_HZ 50
#define RESAMP (SAMPLE_HZ/SAMPLES_PER_BIN/RESAMP_HZ)
#define PWRSUM 20

float resamp_pwr( void )
{
	int i, q, k;
	short ib[ 2*RESAMP*sizeof( short) ];
	
	if( read( 0, ib, sizeof ib ) <= 0 ) {
		perror( "tuneup" );
		exit( 1 );
	}
	
	i = q = 0;
	for( k = 0; k < RESAMP; k += 2 ) {
		i += ib[ k ];
		q += ib[ k + 1 ];
	}
	
	return ((float) i) * ((float) i) + ((float) q) * ((float) q);
}


float sum_pwr( void )
{
	int i;
	float p;
	
	for( i = 0; i < PWRSUM; i += 1 ) p += resamp_pwr();
	
	return p;
}
	


int main(int argc,char *argv[])
{
	for(;;) {
		if( printf( "%f\n", sum_pwr()) <= 0 ) {
			perror( "tuneup" );
			exit( 1 );
		}
	}
}


/*
 * $Log$
 * Revision 1.3  2009-06-22 16:33:32  jpd
 * Fix tuneup cadence.
 *
 * Revision 1.2  2009-06-22 00:35:38  jpd
 * First light.
 *
 * Revision 1.1  2009-06-21 22:04:57  jpd
 * Share parameters.
 * Tuneup filter.
 *
 */
