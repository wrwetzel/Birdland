#!/usr/bin/python
# --------------------------------------------------------------------------
#   check-pages.py - Compare page numbers for each title each book and index source.

#   WRW 22 Dec 2021 -                                                

# --------------------------------------------------------------------------

import os
import sys
import MySQLdb
import click
import collections
import subprocess
import sqlite3
from pathlib import Path

import fb_utils
import fb_config

# --------------------------------------------------------------------------

mismatch = {}
Old_Dc = None

# --------------------------------------------------------------------------
#   Called for one title. Have to check all entries for one title together.
#   Need to rearrange into canonical, sheet, src order so can see all sources for one canonical together.

canon_with_error_counter = collections.Counter()

def inspect_data( data ):
    global canon_with_error_counter

    items = collections.defaultdict( dict )
    items = dict()
    count_match = count_mismatch = 0

    # -------------------------------------------
    #   Title may appear in more than one canonical. Only check for match in the indexes for one canonical at a time.
    #   First group by canonical.                                                                          

    for item in data:
        title =     item[ 'title' ]
        canonical = item['canonical']
        sheet =     item['sheet']
        src =       item['src']
        local =     item['local']
        file =      item['file']
        page =      fb.get_page_from_sheet( sheet, src, local )

        if not page:
            print( f"get_page_from_sheet() returned None, sheet: '{sheet}', src: '{src}', local: '{local}', skipping.", file=sys.stderr, flush=True )
            continue

        if not canonical in items:
            items[ canonical ] = {}
            items[ canonical ][ 'elements' ] = [ { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } ]
            items[ canonical ][ 'title' ] = title
            items[ canonical ][ 'file' ] = file

        else:
            items[ canonical ][ 'elements' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

    # -------------------------------------------
    #   For each canonical check if all pages agree.

    for canonical in items:

        # Check pages for agreement.

        pages = []
        for element in items[ canonical ][ 'elements' ]:
            pages.append( element['page'])

        same = all( x == pages[0] for x in pages )

        # ---------------------------------------
        #   All agree!
        if same:
            count_match += 1

        # ---------------------------------------
        #   Not all agree.
        #   Reference: items[ canonical ][ 'elements' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

        else:
            if True:

                count_mismatch += 1
                canon_with_error_counter[ canonical ] += 1

                title = items[ canonical ][ 'title' ]
                first_sheet = items[ canonical ][ 'elements' ][0]['sheet']

                for element in items[ canonical ][ 'elements' ]:
                    page = element[ 'page' ]
                    sheet = element[ 'sheet' ]
                    src = element[ 'src' ]
                    local = element[ 'local' ]

                    if canonical not in mismatch:              # /// RESUME Once working use setdefault()
                        mismatch[ canonical ] = {}

                    if title not in mismatch[ canonical ]:
                        mismatch[ canonical ][ title ] = { 'first_sheet' : first_sheet, 'data' : [] }

                    mismatch[ canonical ][ title ][ 'data' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

            #   Initially was printing results here rather than accumulating them for later analysis.
            #   Need to sort by title in SELECT to get all titles together

            if False:
                count_mismatch += 1
                canon_with_error_counter[ canonical ] += 1

                count = len( items[ canonical ][ 'elements' ] )
                title = items[ canonical ][ 'title' ]
                file = items[ canonical ][ 'file' ]
                print( f"{title}", flush=True )
                print( f"    {count}\t{canonical}\t{file}", flush=True )

                for element in items[ canonical ][ 'elements' ]:
                    print( f"        s {element['sheet']}\t(p {element['page']})\t{element['src']}\t{element['local']}", flush=True )

                print(flush=True)

    return(count_match, count_mismatch)

# --------------------------------------------------------------------------

def check_pages( dc, all, canon ):

    if all:
        query = """
            SELECT title, titles.src, local, sheet, canonical, file
            FROM titles
            JOIN titles_distinct USING( title_id )
            JOIN local2canonical USING( local, src )
            JOIN canonical2file USING( canonical )
            ORDER BY title
        """
        dc.execute( query )

    elif canon:
        if MYSQL:
            query = """
                SELECT title, titles.src, local, sheet, canonical, file
                FROM titles
                JOIN titles_distinct USING( title_id )
                JOIN local2canonical USING( local, src )
                JOIN canonical2file USING( canonical )
                WHERE canonical = %s
                ORDER BY title
            """
        if SQLITE:
            query = """
                SELECT title, titles.src, local, sheet, canonical, file
                FROM titles
                JOIN titles_distinct USING( title_id )
                JOIN local2canonical USING( local, src )
                JOIN canonical2file USING( canonical )
                WHERE canonical = ?
                ORDER BY title
            """
        data = [canon]
        dc.execute( query, data )

    else:
        print( "You must supply --all or --canon canonical", file=sys.stderr, flush=True )
        # sys.exit(1)
        return 1

    # ------------------------------------------------

    count_match = count_mismatch = 0
    otitle = ''
    data = []

    for row in dc.fetchall():               # Was 'for row in dc:', OK for mysql, not sqlite.
        title = row['title']

        if otitle != title:
            if len( data ) > 1:             # Got multiple of same title, otherwise, nothing to compare
                (cm, cmm) = inspect_data( data )
                count_match += cm
                count_mismatch += cmm
            data = []

        otitle = title
        data.append( row )

    if len( data ) > 1:                     # Do last title.
        (cm, cmm) = inspect_data( data )
        count_match += cm
        count_mismatch += cmm

    # ------------------------------------------------
    #   Show summary of results to stderr.

    print( f"Matches: {count_match}, Mis-Matches: {count_mismatch}", file=sys.stderr, flush=True )
    print( "Remember: Mismatch can occur because of incorrect offset OR errors in incoming index data", file=sys.stderr, flush=True  )

    print( "Mismatches by canonical:", file=sys.stderr, flush=True )
    for canonical in sorted( canon_with_error_counter, key = lambda x: canon_with_error_counter[x] ):
        print( f"  {canon_with_error_counter[ canonical ]:>4} {canonical}", file=sys.stderr, flush=True )

    # -----------------------------------------------------
    #   Show the regrouped details.
    #   Sort by the first sheet found for each of the title group.

    for canonical in mismatch:
        print( f"{'-' * 50}", flush=True )
        print( f"{canonical}", flush=True )

        # Reference: mismatch[ canonical ][ title ][ 'data' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )
        #            mismatch[ canonical ][ title ][ 'first_sheet' ] = page

        # for title in sorted( mismatch[ canonical ], key = lambda x: int( mismatch[canonical][x]['first_sheet'] ) if mismatch[canonical][x]['first_sheet']  else 0 ):
        for title in sorted( mismatch[ canonical ], key = lambda x: int( mismatch[canonical][x]['first_sheet'] ) ):
            print( f"   {title}", flush=True )

            # for item in sorted( mismatch[ canonical ][ title ][ 'data' ], key = lambda x: int(x['page'] if x['page'] else 0 ) ):
            # for item in sorted( mismatch[ canonical ][ title ][ 'data' ], key = lambda x: int(x['page']) ):
            for item in sorted( mismatch[ canonical ][ title ][ 'data' ], key = lambda x: x['src'] ):
                if item['page']:
                    print( f"      (s {item[ 'sheet' ]:>3})    (p {item[ 'page' ]:>3})   {item[ 'src' ]}   {item[ 'local' ]}", flush=True  )

            print( flush=True )

# --------------------------------------------------------------------------

def show_list( dc, item ):
    if MYSQL:
        query = """
            SELECT canonical
            FROM canonicals
            WHERE canonical LIKE %s
            ORDER BY canonical
        """
    if SQLITE:
        query = """
            SELECT canonical
            FROM canonicals
            WHERE canonical LIKE ?
            ORDER BY canonical
        """
    item = f'%{item}%'
    dc.execute( query, [item] )
    for row in dc:
        print( f"'{row[ 'canonical' ]}'", flush=True )

# --------------------------------------------------------------------------
#   /// RESUME - need to pass args, prog_name, and suppress exit.

@click.command()
@click.option( "-d", "--database",      help="Use database sqlite or mysql, default sqlite", default='sqlite' )
@click.option( "-c", "--confdir",               help="Use alternate config directory" )
@click.option( "-v", "--verbose", is_flag=True, help="Show verbose messages" )
@click.option( "-a", "--all",     is_flag=True, help="Process all canonicals" )
@click.option( "-n", "--canon",                 help="Process one canonical" )
@click.option( "-l", "--list",                  help="List canonicals containing arg" )

def do_main( verbose, all, canon, list, database, confdir ):

    # ---------------------------------------------------------------

    global MYSQL, SQLITE, FULLTEXT
    if database == 'sqlite':
        MYSQL = False
        SQLITE = True
        FULLTEXT = False     # True to include Sqlite fulltext index. Only meaningful if get it working better.

    elif database == 'mysql':
        MYSQL = True
        SQLITE = False
        FULLTEXT = False     # True to include Sqlite fulltext index. Only meaningful if get it working better.

    else:
        print( f"ERROR: Specified database '{database}' not supported." )
        rcode = 1
        # sys.exit(1)

    # ---------------------------------------------------------------

    global fb

    fb = fb_utils.FB()
    conf = fb_config.Config()

    fb.set_driver( MYSQL, SQLITE, False )
    conf.set_driver( MYSQL, SQLITE, False )

    # TESTING OUT os.chdir( os.path.dirname(os.path.realpath(__file__)))
    #   Looks like of no concern. Tested OK with '/tmp'
    # os.chdir( os.path.dirname(os.path.realpath(__file__)))

    conf.get_config( confdir )
    conf.set_class_variables()      # WRW 6 Mar 2022 - Now have to do this explicitly
    fb.set_classes( conf )
    fb.set_class_config()

    # ---------------------------------------------------------------
    global Old_Dc

    if MYSQL:
        conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
        c = conn.cursor()
        dc = conn.cursor(MySQLdb.cursors.DictCursor)
        Old_Dc = fb.set_dc( dc )

    elif SQLITE:
        conn = sqlite3.connect( Path( conf.home_confdir, conf.sqlite_database ))     # Note: always in home_confdir
        c = conn.cursor()
        dc = conn.cursor()
        dc.row_factory = sqlite3.Row
        Old_Dc = fb.set_dc( dc )

    else:
        print( "ERROR: No database type specified", file=sys.stderr, flush=True  )
        rcode = 1
        # sys.exit(1)

    # ---------------------------------------------------------------

    if list:
        rcode = show_list( dc, list )

    else:
        if False:       # Helpful to rebuild sheet_offset table while cleaning up the indexes
            # subprocess.run( ['build_tables.py', '--offset' ],
            subprocess.run( ['bl-build-tables', '--offset' ],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

        rcode = check_pages( dc, all, canon )

    # ---------------------------------------------------------------
    
    conn.commit()
    conn.close
    return rcode

# ---------------------------------------------------------------
#   WRW 22 Mar 2022 - Include 'standalone_mode=False' in call to do_main() to prevent
#       click() from exiting at completion. We don't want the exit when calling this
#       from birdland.py as a module.
#   WRW 23 Mar 2022 - Save and restore dc when calling as module. Doesn't seem to matter
#       here as it did with build_tables.py. Because we are not writing to DB here?

def aux_main( args ):
    sys.argv = [ x for x in args ]
    rcode = do_main( standalone_mode=False )
    if Old_Dc:
        fb.set_dc( Old_Dc )
    return rcode

def main():
    rcode = do_main()

if __name__ == '__main__':
    rcode = do_main()

# --------------------------------------------------------------------------
