#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 20 Sept 2020 - Found a bunch of csv fakebook indexes at github

#   Not sure how I got the links-related files, probably manually.
#   Made books.txt and books-unique.txt manually.

#   WRW 12 Mar 2022 - Convert to flat directory for compatibility with
#       python setuptools build process.

#   WRW 6 Apr 2022 - I was going crazy last night trying to harmonize the indexes for
#   'Real Book Vol 2 - Orig'. I'd make a change to the Sheet-Offsets.txt and other
#   pages got shifted. Nothing made sense. Fatigue didn't help. While I'm filtering
#   books with the 'exclude' file here they were leaking back in with the glob() because
#   some of the excluded names are subsets of the included ones and matched. 
#   The leaked books conflicted with the intended ones.
#   A single '_' solved the problem. Not a big deal as I found a couple of other problems
#   along the way.

# ---------------------------------------------------------------------------

import os
import sys
import glob
import pandas as pd
from pathlib import Path

import fb_utils
import fb_config

# ---------------------------------------------------------------------------
#   Note, some files have 4th column with page count for title.

Idir = 'Raw-Index'
Books = 'books-unique.txt'

# ---------------------------------------------------------------------------
#        page;title;last;first;aka;style;tempo;signature;comment;
#   WRW 30 Mar 2020 - Had header=1, should be 0. There is one line of header we are ignoring.

def proc_file( fb, path, book ):

    cols = [0, 1, 2, 3, 4, 5, 6, 7 ]
    col_names = [ 'sheet', 'title', 'last', 'first', 'aka', 'style', 'signature', 'comment' ]

    df = pd.read_csv( path, usecols=cols, names=col_names, header=0, dtype=str, sep=';'  )
    df[ 'first' ] = df[ 'first' ].fillna(0)
    df[ 'last' ] = df[ 'last' ].fillna(0)
    df.sheet = df.sheet.fillna( '-' )

    lineno = 1                      # Start at one because of header on first line.
    for n, s in df.iterrows():
        lineno += 1
        composer = ''
        if s[ 'last' ]:
            composer = s[ 'last' ]
        if s[ 'first' ]:
            if composer:
                composer = composer + " " + s[ 'first' ]
            else:
                composer = s[ 'first' ]

        item = {
            'title' : s[ 'title' ],
            'sheet' :  s[ 'sheet' ],
            'composer' : composer,
            'file'  : Path( path ).name,
            'line'  : lineno,
        }

        fb.add( book, item )

# ---------------------------------------------------------------------------

conf = fb_config.Config()
conf.get_config()
conf.set_class_variables()

fb = fb_utils.FB()
fb.set_classes( conf )
fb.set_class_config()
fb.load_corrections()

excludes = [ x.strip() for x in Path( 'Local-Exclusions.txt' ).read_text().split('\n') ]
omitted_names = set()
included_names = set()

with open( Books ) as bookfd:
    for book in bookfd:
        book = book.strip()
        if book not in excludes:
            included_names.add( book )
            for file in glob.glob( f'{Idir}/{book}_*.pdfb' ):       # WRW 6 Apr 2022 - Adding the '_' resolved an issue bugging me.
                proc_file( fb, file, book )
        else:
            omitted_names.add( book )

fb.save( 'Skrivarna', 'Skr' )

t = '\n   '.join( sorted( included_names ))
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( omitted_names )
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

# ---------------------------------------------------------------------------
