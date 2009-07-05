/* $Id$ */

#include <stdlib.h>
#include "param.h"

/* 
 * Expand the short complex files from wwvbaq to
 * float complex for easy use with numpy.
 */


int main(int argc,char *argv[])
{
	short ib[2*BINS_PER_BUFFER];
	float ob[2*BINS_PER_BUFFER];
	int i,c;
	
	for( ;; ) {
	
		c = read( 0, ib, sizeof ib );
		if( !c ) exit( 0 );
		if( c < 0 ) {
			perror( "complexify" );
			exit( 1 );
		}
		
		for( i = 0; i < 2*BINS_PER_BUFFER; i += 1 )
			ob[i] = (float) ib[i];
		
		c = write( 1, ob, sizeof ob );
		if( c < 0 ) {
			perror( "complexify" );
			exit( 1 );
		}
	}
}

/*
 * $Log$
 * Revision 1.1  2009-07-05 22:09:19  jpd
 * Make complex real data from complex integer samples.
 *
 */


			
	
