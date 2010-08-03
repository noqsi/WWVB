#!/bin/sh

# Grab HTML file with Fermi gamma ray burst data
curl "http://gcn.gsfc.nasa.gov/fermi_grbs.html" | \
# Pipe to awk to extract an XEphem database file from the HTML table
awk -f parse_fermi_grbs.awk > fermi.edb
# Use pyephem to deduce relevant fermi gamma ray burst events
#./find_fermi_events.py > out.tsv

echo
