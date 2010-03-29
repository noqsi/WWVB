#!/bin/sh
# $Id$

while true
do 
	nice -n -20  ./wwvbaq >wwvbcxtemp
	python wwvbred.py >wwvbaq-`date -u +%s`.txt
done

# $Log$
# Revision 1.1  2010-03-29 20:01:26  jpd
# Further fixes for coherent decimation.
#
