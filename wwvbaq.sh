#!/bin/sh
# $Id$

while true
do 
	start=`date -u +%s`
	echo "Start at " $start
	date
	nice -n -20  ./wwvbaq >wwvbcxtemp
	echo -n "End at "
	date
	python wwvbred.py >Data/wwvbaq-${start}.tsv
done

# $Log$
# Revision 1.2  2010-07-25 16:32:39  jpd
# First real production versions.
#
# Revision 1.1  2010-03-29 20:01:26  jpd
# Further fixes for coherent decimation.
#
