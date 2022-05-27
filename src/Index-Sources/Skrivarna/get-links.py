#!/usr/bin/python
# ---------------------------------------------------------------------------------
#   Get links from links.txt
# ---------------------------------------------------------------------------------

import re


Ifile = '../raw-links.txt'      # This is run by get-links.sh from index-files directory
Ifile = 'raw-links.txt'      # This is run by get-links.sh from index-files directory

with open( Ifile ) as ifd:
    for line in ifd:
        for m in re.finditer( '<a href=(.*?)>', line ):
            link = m[1]
            link = link.replace( '"', '' )
            print( link )
