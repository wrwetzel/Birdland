#!/usr/bin/python
# --------------------------------------------------------------------------
#   diff_index.py - Compare page numbers for each title each book and index source.

#   WRW 22 Dec 2021 -                                                

# --------------------------------------------------------------------------

import os
import sys
import click
import collections
import subprocess
import sqlite3
from pathlib import Path
import statistics
from collections import defaultdict

import fb_utils
import fb_config

# --------------------------------------------------------------------------

Old_Dc = None

# --------------------------------------------------------------------------
#   This is pretty cool, saved a lot of convoluted code.

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))

# ------------------------------------------------

def header( canonical ):
    print( f"{'=' * 80}", flush=True )
    print( f"{canonical}", flush=True )
    print( f"{'=' * 80}", flush=True )

# ------------------------------------------------
#   Called for one title. Have to check all entries for one title together.
#   Need to rearrange into canonical, sheet, src order so can see all sources for one canonical together.

def inspect_data_for_one_title( data ):
    global canon_with_error_counter
    global src_coverage_by_title
    global canonicals

    # items = collections.defaultdict( dict )
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
      # file =      item['file']
        page =      fb.get_page_from_sheet( sheet, src, local )

        canonicals.add( canonical )

        if not page:
            print( f"get_page_from_sheet() returned None, sheet: '{sheet}', title: '{title}', src: '{src}', local: '{local}', skipping.", file=sys.stderr, flush=True )
            continue

        if not canonical in items:
            items[ canonical ] = {}
            items[ canonical ][ 'elements' ] = []
            items[ canonical ][ 'title' ] = title
          # items[ canonical ][ 'file' ] = file

        items[ canonical ][ 'elements' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

    # -------------------------------------------
    #   For each canonical check if all pages agree.
    #   items[] is list of pages for title

    for canonical in sorted( items ):
        # Check pages for agreement.

        pages = []
        coverage = []
        coverage.append( items[ canonical ][ 'title' ] )        # first element is title

        for element in items[ canonical ][ 'elements' ]:
            pages.append( element['page'])
            coverage.append( element[ 'src' ] )                 # remaining elements are srcs covering title and canonical

        same = all( x == pages[0] for x in pages[1:] )

        src_coverage_by_title.setdefault( canonical, [] ).append( coverage )

        # ---------------------------------------
        #   All agree!

        if same:
            count_match += 1

        # ---------------------------------------
        #   Not all agree.
        #   Reference: items[ canonical ][ 'elements' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

        else:
            # ---------------------------------------------------------------------------------------------------
            #   WRW 29 Mar 2022 - Exploring statistical analysis of page number differences.                      
            #       Accumulate stats for each canonical by src.

            global delta_by_canon_src
            global delta_count_by_canon_src

            # ---------------------------------------

            ipages = [ int(x) for x in pages ]
            mean = statistics.mean( ipages )  

            for element in items[ canonical ][ 'elements' ]:
                page = int( element['page'] )
                src =  element['src']
                delta = abs( mean - page )

                delta_by_canon_src[ canonical ][ src ] += delta
                delta_count_by_canon_src[ canonical ][ src ] += 1

            # ---------------------------------------------------------------------------------------------------

            count_mismatch += 1
            canon_with_error_counter[ canonical ] += 1

            title = items[ canonical ][ 'title' ]
            first_sheet = items[ canonical ][ 'elements' ][0]['sheet']

            for element in items[ canonical ][ 'elements' ]:
                page = element[ 'page' ]
                sheet = element[ 'sheet' ]
                src = element[ 'src' ]
                local = element[ 'local' ]

                mismatch[ canonical ] = mismatch.setdefault( canonical, {} )
                mismatch[ canonical ][ title ] = mismatch[ canonical ].setdefault( title, { 'first_sheet' : first_sheet, 'data' : [] } )
                mismatch[ canonical ][ title ][ 'data' ].append( { 'page' : page, 'sheet' : sheet, 'src' : src, 'local' : local } )

    return(count_match, count_mismatch)

# --------------------------------------------------------------------------

def check_pages( dc, all, canon ):

    if all:
        query = """
            SELECT title, titles.src, local, sheet, canonical /*, file */
            FROM titles
            JOIN titles_distinct USING( title_id )
            JOIN local2canonical USING( local, src )
            /* JOIN canonical2file USING( canonical ) */
            ORDER BY title
        """
        dc.execute( query )

    elif canon:
        if MYSQL:
            query = """
                SELECT title, titles.src, local, sheet, canonical /*, file */
                FROM titles
                JOIN titles_distinct USING( title_id )
                JOIN local2canonical USING( local, src )
                /* JOIN canonical2file USING( canonical ) */
                WHERE canonical = %s
                ORDER BY title
            """
        if SQLITE:
            query = """
                SELECT title, titles.src, local, sheet, canonical /*, file */
                FROM titles
                JOIN titles_distinct USING( title_id )
                JOIN local2canonical USING( local, src )
                /* JOIN canonical2file USING( canonical ) */
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
    #   WRW 12 Apr 2022 - Missing a few titles, think problem may be here.
    #       Yup, stupid bug in recognizing change in title as row fetched. Abandon that approach and
    #       build dict of all titles instead. Much cleaner.

    count_match = count_mismatch = 0
    data_by_title = {}

    for row in dc.fetchall():               # Was 'for row in dc:', OK for mysql, not sqlite.
        data_by_title.setdefault( row[ 'title' ], [] ).append( row )

    for title in data_by_title:             # Inspect by title.
        (cm, cmm) = inspect_data_for_one_title( data_by_title[ title ] )        # *** Do it!
        count_match += cm
        count_mismatch += cmm

    # ------------------------------------------------------------
    #   Show summary of results to stderr.

    if gsummary:
        print( f"Matches: {count_match}, Mis-Matches: {count_mismatch}", flush=True )

        print( "Page mismatches by canonical:", flush=True )
        print( "Mismatches occur because sheet offset misalignment or errors in incoming index data.", flush=True  )
        for canonical in sorted( canon_with_error_counter, key = lambda x: canon_with_error_counter[x] ):
            print( f"  {canon_with_error_counter[ canonical ]:>4} {canonical}", flush=True )
        print('')

    # -----------------------------------------------------
    #   WRW 12 Apr 2022 - Partial coverage here not agreeing with fb_index_diff.py. Looks like prviously only
    #       checking for partials for titles with page number diffferences, not all titles.
    #       Change loop below from mismatches to canonicals.

    #   Show the regrouped details.
    #   Sort by the first sheet found for each of the title group.

    # for canonical in mismatch:

    for canonical in sorted( canonicals ):
        show_header = True

        if gverbose:
            if canonical in mismatch:
                if show_header:
                    header( canonical )
                    show_header = False

                for title in sorted( mismatch[ canonical ], key = lambda x: int( mismatch[canonical][x]['first_sheet'] ) ):
                    print( f"   {title}", flush=True )
                    for item in sorted( mismatch[ canonical ][ title ][ 'data' ], key = lambda x: x['src'] ):
                        if item['page']:
                            print( f"      (s {item[ 'sheet' ]:>3})    (p {item[ 'page' ]:>3})   {item[ 'src' ]}   {item[ 'local' ]}", flush=True  )

                    print( flush=True )

        # -----------------------------------------------------
        #   Remember:
        #   src_coverage_by_title[ canonical ] and c: c[0] is title, c[1:] are srcs covering title.

        all_srcs = set()                # Srcs that appear for all titles.
        for c in src_coverage_by_title[ canonical ]:     # Make pass over all coverage to accumulate all srcs appearing.
            all_srcs |= set( c[1:] )

        first = True
        for c in src_coverage_by_title[ canonical ]:     # A second pass to compare srcs for each title against all.
            tsrc = set( c[1:] )     # Set of srcs for one title.
            if all_srcs != tsrc:

                canon_with_partial_counter[ canonical ] = canon_with_partial_counter.setdefault( canonical, 0 ) + 1

                if gverbose:
                    if show_header:
                        header( canonical )
                        show_header = False

                    if first:
                        # print( canonical )
                        print( f"     {'Title':>40}  {'Missing in index from':<30} ", flush=True )
                        print( f"     {'-'*40}  {'-'*30} ", flush=True )
                        first = False

                    missing = ', '.join( [ x for x in sorted( all_srcs - tsrc ) ] )
                    print( f"     {c[0]:>40}  {missing:<30} ", flush=True )

            # print( flush=True )

    # -----------------------------------------------------

    if gsummary:
        print( "Partial coverage by canonical:", flush=True )
        print( "Partial coverage occurs because of differences in spelling of titles or missing titles.", flush=True )
        for canonical in sorted( canon_with_partial_counter, key = lambda x: canon_with_partial_counter[x] ):
            print( f"  {canon_with_partial_counter[ canonical ]:>4} {canonical}", flush=True )

    # -----------------------------------------------------
    #   WRW 29 Mar 2022 - Show statistical data

    if gpage_summary:
        print( "Summary of differences in page numbers for given title by canonical and src for canonicals with mismatches:" )
        for canonical in delta_by_canon_src:
            print( canonical, flush=True )
            for src in delta_by_canon_src[ canonical ]:
                n = delta_count_by_canon_src[ canonical ][ src ]
                a = delta_by_canon_src[ canonical ][ src ] / n
                print( f"   {src}: titles with mismatches: {n}, avg difference: {a:.2f}", flush=True )
            print(flush=True)

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

@click.command()
@click.option( "-d", "--database",                          help="Use database sqlite or mysql, default sqlite", default='sqlite' )
@click.option( "-c", "--confdir",                           help="Use alternate config directory" )
@click.option( "-v", "--verbose", is_flag=True,             help="Show verbose messages" )
@click.option( "-a", "--all",     is_flag=True,             help="Process all canonicals" )
@click.option( "-n", "--canon",                             help="Process one canonical" )
@click.option( "-l", "--list",                              help="List canonicals containing arg" )
@click.option( "-s", "--summary", is_flag=True,             help="Show summary of mismatch and coverage" )
@click.option( "-p", "--page_summary",  is_flag=True,       help="Show summary of differences in page numbers" )

def do_main( verbose, all, canon, list, database, confdir, summary, page_summary ):

    # ---------------------------------------------------------------
    global canon_with_error_counter, delta_by_canon_src, delta_count_by_canon_src, mismatch, src_coverage_by_title
    global canon_with_partial_counter, canonicals
    global gverbose, gsummary, gpage_summary

    gverbose = verbose
    gsummary = summary
    gpage_summary = page_summary

    canon_with_partial_counter = dict()
    canon_with_error_counter = collections.Counter()
    delta_by_canon_src = nested_dict( 2, int )                      # WRW 29 Mar 2022 - accumulate page mismatch stats
    delta_count_by_canon_src = nested_dict( 2, int )
    mismatch = {}

    src_coverage_by_title = {}
    canonicals = set()

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
        import MySQLdb
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
            subprocess.run( ['build_tables.py', '--offset' ],
          #   subprocess.run( ['bl-build-tables', '--offset' ],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

        rcode = check_pages( dc, all, canon )

    # ---------------------------------------------------------------
    
    # conn.commit()
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
