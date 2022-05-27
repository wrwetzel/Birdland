#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 25 Apr 2022 - do-user.py - Build the json files for user-created indexes.
#   Taken from do_adamspiers.py

#   Files created by db_create_index.py
#   Don't bother with pandas for this since we control both ends.
#   Build Sheet-Offsets.py

#   CSV Format:
#       Title, page, sheet
#       Title may be '--Skip--'
# ---------------------------------------------------------------------------

import sys
import os
import re
from pathlib import Path
import csv

import fb_utils
import fb_config

# ---------------------------------------------------------------------------

Root = 'Raw-Index'

# ---------------------------------------------------------------------------
#   Read CSV file with Pandas into list of title, page.
#   Remove (key)* in GreatGigBook. 
#       title = re.sub( ' \(.*?\)\*?$', '', title )
#       WRW 3 Apr 2022 - Woody'n You (Algo Bueno) had (Algo Bueno) removed. Probably others. Ouch!
#       Already doing (key)* removal in fb_title_correction.py.

def proc_file( fb, path, book, so_file ):

    so_table = []
    old_offset = 99999

    with open( path, "r", newline='' ) as fd:
        reader = csv.reader( fd )
        lineno = 0
        for row in reader:
            lineno += 1
            title = row[0]
            page  = row[1]
            sheet = row[2]

            if title.startswith( '#' ) or title == '--Skip--':
                continue

            # ---------------------------------------------------------------
            #   Some OCR issues
            title = title.replace( '|', 'I' )        # Confuses I for vertical bar

            item = {
                'title' : title,
                'sheet' : sheet,
                'file'  : path.name,
                'line'  : lineno,
            }

            fb.add( book, item )
            offset = int(page) - int(sheet)
            if offset != old_offset:
                so_table.append( f"({sheet}, {offset})" )
                old_offset = offset

    # ------------------------------------------------

    out_lines = [ so_table[i:i + 8] for i in range(0, len(so_table), 8)]
    ary = []
    for out_line in out_lines:
        ary.append(  ' '.join( out_line ) )

    txt = f"{book} | " + ' \\\n    '.join( ary ) + '\n'

    so_file.write( txt )

    # ------------------------------------------------


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
so_file = conf.val( 'sheetoffsets', 'User' )

with open( so_file, 'w' ) as so_fd:
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
                    proc_file( fb, path, stem, so_fd )
                    included_names.add( stem )
    
                else:
                    omitted_names.add( stem )


t = '\n   '.join( included_names )
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( omitted_names )
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

fb.save( 'User', 'Usr' )

# ---------------------------------------------------------------------------
