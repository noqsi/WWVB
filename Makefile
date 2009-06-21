# $Id$

wwvbaq : wwvbaq.c param.h
	$(CC) -o wwvbaq -lm -lcomedi wwvbaq.c

tuneup: param.h tuneup.c
	$(CC) -o tuneup tuneup.c

# $Log$
# Revision 1.2  2009-06-21 22:04:57  jpd
# Share parameters.
# Tuneup filter.
#
# Revision 1.1  2009-06-16 00:02:18  jpd
# Timing test.
#
