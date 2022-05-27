#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 20 Sept 2020 - Found a bunch of csv fakebook indexes at github
# ---------------------------------------------------------------------------

#   WRW 28 Apr 2022 - Want to edit input but tsv is problematic. Converted to csv with:

# awk 'BEGIN { FS="\t"; OFS="," } {
#   rebuilt=0
#   for(i=1; i<=NF; ++i) {
#     if ($i ~ /,/ && $i !~ /^".*"$/) {
#       gsub("\"", "\"\"", $i)
#       $i = "\"" $i "\""
#       rebuilt=1
#     }
#   }
#   if (!rebuilt) { $1=$1 }
#   print
# }' sher.tsv > sher.csv

import sys
import os
import pandas as pd

import fb_utils
import fb_config
from pathlib import Path

# ---------------------------------------------------------------------------

# Ifile = 'sher.tsv'
Ifile = Path( 'Raw-Index', 'sher.csv' )

# ---------------------------------------------------------------------------

def proc_file( fb, ifile ):

    omitted_names = set()
    included_names = set()

    cols = [0, 1, 2, 3 ]
    col_names = [ 'title', 'composer', 'book', 'sheet' ]

    # df = pd.read_csv( ifile, usecols=cols, names=col_names, header=None, dtype=str, sep='\t'  )
    df = pd.read_csv( ifile.as_posix(), usecols=cols, names=col_names, header=None, dtype=str )
    df.sheet = df.sheet.fillna( '-' )
    df.composer = df.composer.fillna( '-' )
    local_names = df.book.unique().tolist()

    excludes = [ x.strip() for x in Path( 'Local-Exclusions.txt' ).read_text().split('\n') ]  

    for x in excludes:                  # Remove file names in Local-Exclusions.text from local_names
        if x in local_names:
            local_names.remove(x)

    lineno = 0
    for n, s in df.iterrows():
        lineno += 1
        book = s[ 'book' ]
        if book in local_names:
            item = {
                'title' : s[ 'title' ],
                'composer' : s[ 'composer' ],
                'sheet' :  s[ 'sheet' ],
                'file'  : ifile.name,
                'line'  : lineno,
            }
            fb.add( book, item )
            included_names.add( book )

        else:
            omitted_names.add( book )

    t = '\n   '.join( sorted( included_names ))
    print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

    t = '\n   '.join( omitted_names )
    print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

# ---------------------------------------------------------------------------

conf = fb_config.Config()
conf.get_config()
conf.set_class_variables()

fb = fb_utils.FB()
fb.set_classes( conf )
fb.set_class_config()
fb.load_corrections()

proc_file( fb, Ifile )
fb.save( 'Sher', 'Shr' )

# ---------------------------------------------------------------------------
