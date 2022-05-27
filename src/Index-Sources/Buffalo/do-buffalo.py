#!/usr/bin/python
# ----------------------------------------------------------------------------
#   WRW 18 Sept 2020 - Explore Buffalo Fake Book Index
#   Each index item is 36 lines

#   WRW 7 Mar 2022 - Reduce this to take input from csv 
#       file produced by extract-csv-from-html.py.

# ----------------------------------------------------------------------------

import os
import sys
import collections
from pathlib import Path
import csv
import gzip

import fb_utils
import fb_config

# ----------------------------------------------------------------------------

excluded_names = set()
included_names = set()
excludes = [ x.strip() for x in Path( 'Local-Exclusions.txt' ).read_text().split('\n') ]

# ----------------------------------------------------------------------------
#   CSV produced by:
#       csvwriter.writerow( [book, content['title'], content[ 'sheet' ], content['composer'], content['lyricist'] ]

def proc_item( fb, item, file, lineno ):
    book = item[0]
    title = item[1]
    sheet = item[2]
    composer = line[3]
    lyricist = line[4]

    # ------------------------------------------------------------------------
    if book not in excludes:
        #   Print results for examination / testing
        #       print( f'{title}\n  {composer}\n  {lyricist}\n  {book}\n  {page}' )

        item = { 'title' : title,
                 'composer': composer,
                 'lyricist': lyricist,
                 'sheet': sheet,
                 'file'  : file.name,
                 'line'   : lineno,
               }

        if lyricist != '-' and lyricist != '--':
            item[ 'lyricist' ] = lyricist

        fb.add( book, item )
        included_names.add( book )

    else:
        excluded_names.add( book )

# ----------------------------------------------------------------------------

conf = fb_config.Config()
conf.get_config()
conf.set_class_variables()

fb = fb_utils.FB()
fb.set_classes( conf )
fb.set_class_config()
fb.load_corrections()

Buffalo_csv_file = Path( 'Raw-Index', 'buffalo-index.csv.gz' )

# with open( Buffalo_csv_file ) as ifd:
with gzip.open( Buffalo_csv_file.as_posix(), 'rt' ) as ifd:
    csvreader = csv.reader( ifd )
    lineno = 0
    for line in csvreader:
        lineno += 1
        proc_item( fb, line, Buffalo_csv_file, lineno )

# ------------------------------------------------------------------------

fb.save( "Buffalo", "Buf" )

t = '\n   '.join( sorted( included_names ))
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( excluded_names )
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

# ----------------------------------------------------------------------------
