# $Id$

all :	wwvbaq tuneup complexify

wwvbaq : wwvbaq.c param.h
	$(CC) -o wwvbaq -lm -lcomedi wwvbaq.c

tuneup: param.h tuneup.c
	$(CC) -o tuneup tuneup.c

complexify: param.h complexify.c
	$(CC) -o complexify complexify.c

# $Log$
# Revision 1.4  2009-07-05 22:09:19  jpd
# Make complex real data from complex integer samples.
#
# Revision 1.3  2009-06-22 00:35:38  jpd
# First light.
#
# Revision 1.2  2009-06-21 22:04:57  jpd
# Share parameters.
# Tuneup filter.
#
# Revision 1.1  2009-06-16 00:02:18  jpd
# Timing test.
#
