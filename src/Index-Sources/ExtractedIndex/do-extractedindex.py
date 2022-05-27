#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 27 Dec 2021 - Realized I could extract indexes from pdf files.
#       Input is from extract-index-from-pdf.py

#   Local book name is same as file name in incoming data.
#   WRW 28 Dec 2021 - Added 'Proto' files as starting point for hand editing.
#   WRW 2 Apr 2022 - Some titles in 101 Hits for Buskers - Book 02.pdf have
#       a trailing 'A'/'B', most likely for two-page songs. Remove it
#       before it gets into title correction and the A moved to the front.

# ---------------------------------------------------------------------------

import sys
import os
import re
import pandas as pd
import socket
import math
from pathlib import Path

import fb_utils
import fb_config

# ---------------------------------------------------------------------------
#   Note, some files have 4th column with page count for title.

Ifile = Path( 'Raw-Index', 'extracted.csv' )
included_names = set()
excluded_names = set()

excludes = [ x.strip() for x in Path( 'Local-Exclusions.txt' ).read_text().split('\n') ]

# ---------------------------------------------------------------------------

def proc_file( fb, ifile ):

    cols = [0, 1, 2, 3 ]
    col_names = [ 'rpath', 'file', 'title', 'sheet' ]

    df = pd.read_csv( ifile.as_posix(), usecols=cols, names=col_names, header=None, dtype=str, keep_default_na=False  )
    df.sheet = df.sheet.fillna( '-' )
    df.title = df.title.dropna()        # Saw a nan in title, from empty field, i.e. ''

    lineno = 0
    for n, s in df.iterrows():
        lineno += 1
        file = s[ 'file' ]
        rpath = s[ 'rpath' ]

        book, ext = os.path.splitext( file )
        if book not in excludes:
            fb.set_music_file( book, os.path.join( rpath, file ))

            otitle = s[ 'title' ]
            m = re.match( '(.*)(A|B)$', otitle )
            if m:
                title = f"{m[1]}"
                # print( "/// removed trailing A|B:", otitle, "->", title )
            else:
                title = otitle

            item = {
                'title' : title,
                'sheet' :  s[ 'sheet' ],
                'file'  : ifile.name,
                'line'  : lineno,
            }
            fb.add( book, item )
            included_names.add( book )
        else:
            excluded_names.add( book )

# ---------------------------------------------------------------------------

conf = fb_config.Config()
conf.get_config()
conf.set_class_variables()

fb = fb_utils.FB()
fb.set_classes( conf )
fb.set_class_config()
fb.load_corrections()

proc_file( fb, Ifile )
fb.save( 'ExtractedIndex', 'Ext' )

t = '\n   '.join( sorted( included_names ))
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( excluded_names )
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

# ---------------------------------------------------------------------------
