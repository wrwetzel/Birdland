#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 20 Sept 2020 - Found a bunch of csv fakebook indexes at github

#   Build json file of titles and pages in common dir for all sources.
#   Program similar to this for each source.

#   WRW 1 Mar 2022 - Change approach to remove use of fb.get_local_names().
#   WRW 13 Apr 2022 - Great Gig Book has key sometimes in parens with no asterisk.
#       Remove here as doing it in fb_title_correction.py may break other things,
#       specifically 'A' in parens.

# ---------------------------------------------------------------------------

import sys
import os
import re
import pandas as pd
from pathlib import Path

import fb_utils
import fb_config

# ---------------------------------------------------------------------------
#   Note, some files have 4th column with page count for title.

Root = 'Raw-Index'

# ---------------------------------------------------------------------------
#   Read CSV file with Pandas into list of title, page.
#   Remove (key)* in GreatGigBook. 
#       title = re.sub( ' \(.*?\)\*?$', '', title )
#       WRW 3 Apr 2022 - Woody'n You (Algo Bueno) had (Algo Bueno) removed. Probably others. Ouch!
#       Already doing (key)* removal in fb_title_correction.py.

def proc_file( fb, path, book ):
    base = os.path.basename( path )

    cols = [ 0, 1 ]
    col_names = [ 'title', 'sheet' ]

    df = pd.read_csv( path, usecols=cols, names=col_names, header=None, dtype=str, sep=','  )
    df.sheet = df.sheet.fillna( '-' )
    lineno = 0
    for n, s in df.iterrows():
        lineno += 1
        title = s[ 'title' ]        
        if title.startswith( '#' ):
            continue

        #   WRW 13 Apr 2022 - Other srcs have it too, move to fb_title_correction.py 
        if False and book == 'GreatGigBook':
            m = re.match( '(.*)\s+((\(Gm\)|\(A\)|\(Bm\)|\(Fm\)|\(D\)|\(Em\)|\(Cm\)|\(Am\)|\(Dm\)|\(G\)|\(C\)|\(F\)|\(Bb\)|\(Db\)|\(Eb\)|\(Bass\)|\(Ab\))\*?)$', title )
            if m:
                ntitle = f"{m[1]}"
                # print( f"Trailing (key) '{m[2]}': '{title}' -> '{ntitle}'" )
                title = ntitle

        item = {
            'title' : title,
            'sheet' : s[ 'sheet' ],
            'file'  : path.name,
            'line'  : lineno,
        }

        fb.add( book, item )

# ---------------------------------------------------------------------------
#   Read each file starting at Root ('book-indices-master').
#   Save in IndexDir ('/home/wrw/Library/FBIndex/Index.Json') in file named by source_short and local book name.
#   cwd is AdamSpiers when this is launched. It is set by built-tables.py before running this.

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

for dir, dirs, files in os.walk( Root ):
    # print('Directory: %s' % dir, flush=True )

    for file in files:
        if file.startswith( ',' ):      # Ignore ,* files, backups from the Rand editor.
            continue

        path = Path( dir, file )
        ext = path.suffix
        name = path.name
        stem = path.stem

        if ext == '.csv':

            if stem not in excludes:
                proc_file( fb, path, stem )
                #  print( f'  {path}', flush=True )
                included_names.add( stem )

            else:
                omitted_names.add( stem )     


t = '\n   '.join( included_names )
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( omitted_names )
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

fb.save( 'AdamSpiers', 'Asp' )

# ---------------------------------------------------------------------------
