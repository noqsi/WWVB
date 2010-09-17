#!/bin/bash

shopt -u failglob

for i in *.tsv ; do 
        if [ -f $i ] ; then
                echo "mv $i Data/" 
                mv $i Data/ 
        fi      
done  
