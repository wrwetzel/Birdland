#!/usr/bin/python
# ----------------------------------------------------------------------------------
#   WRW 4 Dec 2021
#   Exploring makeing a file/page of YouTube links from a list of titles in fakebook.
#   Migrate to using existing .json files
#   Save YouTube data in .json file, not html, so can build DB with data without going back
#       to Youtube.

#   Install: 'youtube-search-python' from AUR with paru

#   WRW 9 Dec 2021 - A slightly different approach. Build one output file
#       not distinguished by source or book, just by title.
#       Work from distinct titles table

#   Works from titles_distinct. Run this after that is built. Will have to rerun build-tables.py again
#       to build title2youtube table with data obtained here.

#   WRW 26 Mar 2022 - Convert to current conventions of config file and database

# ----------------------------------------------------------------------------------

from youtubesearchpython import VideosSearch
import sys
import os
import json
import gzip
import click
import sqlite3
from pathlib import Path

import fb_config

# ----------------------------------------------------------------------------------

# DB = 'Birdland'
# Odir =  "/home/wrw/Library/FBIndex/YT.Json"
# Ofile = 'Titles.json'

# ----------------------------------------------------------------------------------
#   For debugging

def show_results( results ):
    for result in results:
        print( "=============================" )
        print( result[ 'title' ] )
        print( "  link:", result[ 'link' ] )
        print( "  type:", result[ 'type' ] )
        print( "  duration:", result[ 'duration' ] )
        print( "  publishedTime:", result[ 'publishedTime' ] )
        print( "  view count:" )
        print( "    text:", result[ 'viewCount' ][ 'text' ] )
        print( "    short:", result[ 'viewCount' ][ 'short'] )
        print( "  channel:" )
        print( "    name:", result[ 'channel' ][ 'name' ] )
        print( "    id:", result[ 'channel' ][ 'id' ] )
        print( "    link:", result[ 'channel' ][ 'link' ] )
    
        print( "  shelfTitle:", result[ 'shelfTitle' ] )
        print( "  descriptionSnippet:" )
        if result[ 'descriptionSnippet' ]:
            for ds in result[ 'descriptionSnippet' ]:
                print( "    ", ds[ 'text' ] )
    
        if True:
            print( "-----------------------------" )
            for k in result.keys():
                 print( f"       {k}: {result[ k ]}" )
    
        print( "" )

# ----------------------------------------------------------------------------------

@click.command( context_settings=dict(max_content_width=120) )
@click.option( "-c", "--confdir",               help="Use alternate config directory" )
@click.option( "-d", "--database",      help="Use database sqlite or mysql, default sqlite", default='sqlite' )
def do_query( confdir, database ):

    global fb, conf

    # ---------------------------------------------------------------
    #   Now support both databases. Select by command-line option, not config-file option

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
        print( f"ERROR: Specified database '{database}' not supported.", file=sys.stderr )
        sys.exit(1)

    # ---------------------------------------------------------------

    conf = fb_config.Config()
    conf.set_driver( MYSQL, SQLITE, False )

    os.chdir( os.path.dirname(os.path.realpath(__file__)))      # Run in directory where this lives.

    conf.get_config( confdir )
    conf.set_class_variables()      # WRW 6 Mar 2022 - Now have to do this explicitly

    # ---------------------------------------------------------------

    if MYSQL:
        import MySQLdb
        conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
        c = conn.cursor()
        dc = conn.cursor(MySQLdb.cursors.DictCursor)

    elif SQLITE:
        conn = sqlite3.connect( Path( conf.home_confdir, conf.sqlite_database ))     # Note: always in home_confdir
        c = conn.cursor()
        dc = conn.cursor()
        dc.row_factory = sqlite3.Row

    else:
        print( "ERROR: No database type specified", file=sys.stderr, flush=True  )
        sys.exit(1)

    # ---------------------------------------------------------------

    limit = 0

    title_counter = 0
    contents = []

    query = "SELECT title FROM titles_distinct ORDER BY title"
    dc.execute( query )
    rows = dc.fetchall()
    for row in rows:

        title = row['title']
        links = []

        print( f"{row['title']}")

        try:
            t = VideosSearch( row['title'], limit = 10 )        # limit is max number of links to return
            results = t.result()['result']

            # show_results( results ) # ///

            for result in results:
                # url = result[ 'link' ]
                ytitle = result[ 'title' ]
                id = result[ 'id' ]
                duration = result[ 'duration' ]

                # t = { 'title' : title, 'duration': duration, 'url' : url }
                t = { 'ytitle' : ytitle, 'duration': duration, 'id' : id }
                links.append( t )

        except Exception as e:
            (type, value, traceback) = sys.exc_info()
            print( f"VideosSearch failed on search for {title}: type: {type}, value: {value}", file=sys.stderr )

        t = { 'title' : title, 'links' : links }
        contents.append( t )
        title_counter += 1
        if limit != 0 and title_counter >= limit:
            break

    full_contents = { 'contents' : contents }
    json_text = json.dumps( full_contents, indent=2 )
    ofile = Path( conf.val( 'youtube_index' ) )
    with gzip.open( ofile, 'wt' ) as ofd:
        ofd.write( json_text )

# ----------------------------------------------------------------------------------

if __name__ == '__main__':
    do_query()
    conn.close

# ----------------------------------------------------------------------------------
