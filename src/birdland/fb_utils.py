#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 21 Sept 2020 - fb_utils.py - utilities for building fakebook index
# ---------------------------------------------------------------------------

import json
import os
import sys
import collections
import glob
import re
import MySQLdb
import configparser
import socket
import subprocess
import shutil
from pathlib import Path
import inspect
import gzip
import ctypes
import csv

import fullword
import fb_title_correction

# ---------------------------------------------------------------------------
#   Note, some index files have 4th column with page count for title.
#   Move some to config file? No, all remaining are only used here.
#   Moved MusicIndexDir to config file and changed fakebookifile to youtube_index

Proto_Local2Canon =     'Proto-Local2Canon.txt'
Proto_Sheet_Offsets =   'Proto-Sheet-Offsets.txt'
Proto_Canonical2File =  'Proto-Canonical2File.txt'
DocFile =               'birdland.pdf'
BL_Icon =               'Icons/Bluebird-64.png'

ignore_words = set( ['mid', 'pdf'] )    # used in my_match()

# ---------------------------------------------------------------------------
#   This is where folder names for specific sources come from. Still relevant.
#   WRW 2 Mar 2022 - Trying to work only from source names in config file.

OMIT_src2source = {
    'Asp' :  'AdamSpiers',
    'Buf' :  'Buffalo',
    'Ext' :  'ExtractedIndex',
    'Mik' :  'MikelNelson',
    'Shr' :  'Sher',
    'Skr' :  'Skrivarna',
    'Jad' :  'JasonDonenfeld',
    'Stm' :  'StompBox',
}

# ---------------------------------------------------------------------------
#   Replace spaces with underscores and path separators with dash so can
#       keep these files in flat directory hierarchy.

def clean_filename( name ):
    name = name.replace( " ", "_" )
    name = name.replace( "/", "-" )
    return name

# ---------------------------------------------------------------------------
#   Replace %s with ? if using SQLITE

def fix_query( query ):
    if SQLITE:
        query = query.replace( '%s', '?' )
    return query

# ---------------------------------------------------------------------------

dc = None

class FB():

    def __init__( self ):
        self.books = {}
        self.music_popen = None
        self.audio_popen = None
        self.midi_popen = None
        self.youtube_popen = None
        self.doc = None
        self.cur_page = None
        self.music_files = {}
        self.zoom = 1
        self.zoom_set = False
        self.fit = 'Height'
        self.config_file = None
        self.save_music_file = None
        self.log_data = []
        self.log_histo_data = {}

        #   For testing fb_title_correction.py on the raw data. 
        #       Set log below 
        #       build-tables.py --convert_raw

        # self.corrections_log  = open( "/tmp/Title-corrections.txt", "a" )   # Remember to clear file before each execution of birdland.py
        self.corrections_log  = None                                                                                          

    # ------------------------------------------------------------------------
    #   Set configuration parameters in class variables.
    #   This is vestigal from when the parameters were included in this module.
    #   Eventually migrate to referencing conf.v directly. NO! conf.val( 'config-id' )

    def set_class_config( self ):

        self.Music_File_Folders =       self.conf.val('music_file_folders')
      # self.Music_File_Extensions =    self.conf.val('music_file_extensions')
        self.Audio_File_Extensions =    self.conf.val('audio_file_extensions')
      # self.Index_Sources =            self.conf.val( 'index_sources' )
    
        self.Music_File_Root =          self.conf.val('music_file_root')
        self.Midi_File_Root =           self.conf.val('midi_file_root')
        self.Audio_File_Root =          self.conf.val('audio_file_root')
        self.Audio_Folders =            self.conf.val('audio_folders')
        self.Midi_Folders =             self.conf.val('midi_folders')

        self.Canonicals =               self.conf.val('canonicals')
        self.Canonical2File =           self.conf.val('canonical2file')
      # self.Local2Canon =              self.conf.val('local2canon')
        self.YouTubeIndex =             self.conf.val('youtube_index')
      # self.SheetOffsets =             self.conf.val('sheetoffsets')
        self.UseExternalMusicViewer =   self.conf.val('use_external_music_viewer')
        self.ShowIndexMgmtTabs =        self.conf.val('show_index_mgmt_tabs')

        self.ExternalMusicViewer    =   self.conf.val( 'external_music_viewer' )
        self.ExternalAudioPlayer    =   self.conf.val( 'external_audio_player' )
        self.ExternalMidiPlayer    =    self.conf.val( 'external_midi_player' )
        self.ExternalYouTubeViewer =    self.conf.val( 'external_youtube_viewer' )
        self.Source_Priority =          self.conf.val('source_priority')
    
        self.MusicIndexDir =            self.conf.val('music_index_dir')

    # ------------------------------------------------------------------------
    #   WRW 23 Mar 2022 - Need to save and restore dc using fb_utils from
    #   build_tables.py and check_offsets.py running as modules, not separate
    #   commands.

    def set_dc( self, t ):
        global dc
        old_dc = dc
        dc = t
        return old_dc

    # ------------------------------------------------------------------------

    def set_driver( self, t1, t2, t3 ):
        global MYSQL, SQLITE, FULLTEXT
        MYSQL = t1
        SQLITE = t2
        FULLTEXT = t3

    def get_driver( self ):
        if MYSQL:
            return 'mysql'
        if SQLITE:
            return 'sqlite'

        return None

    # ------------------------------------------------------------------------

    def set_classes( self, conf ):
        self.conf = conf

    # ------------------------------------------------------------------------

    def get_docfile( self ):
        return DocFile

    # ------------------------------------------------------------------------
    #   WRW 15 Feb 2022 - An another approach to full-text matching without using Sqlite USING fts5()
    #       Either I'm missing something or fulltext is not working well in Sqlite.

    #       Quoted strings match exactly.
    #       Otherwise match all words.
    #       RESUME - remove stop words - a, the, etc?

    #       Save, now doing parameter substitution and don't need this:
    #           s = s.replace( "'", "''" )      # Escape single quote with ''
    #           s = s.replace( '\\', '\\\\' )   # Escape backslash with \\ so don't escape single quote when at end of field.

    # The REGEXP operator is a special syntax for the regexp() user
    # function.  No regexp() user function is defined by default and so use of
    # the REGEXP operator will normally result in an error message.  If an
    # application-defined SQL function named "regexp" is added at run-time, then
    # the "X REGEXP Y" operator will be implemented as a call to "regexp(Y,X)".

    #   Experimental pseudo fullword matching attempt. This has the potential to be really cool as
    #       I can tailor it specifically to the application.
    #   Match search string 'words' against column data 'data'. Return True if match.
    #   /// RESUME - think about doing this in C, maybe cffi? Great candidate for optimization.
    #       data: filename, song title
    #       words: 'love me tender'

    # ----------------------------------------
    #   WRW 16 Feb 2022 - I had a lot of problems with Sqlite3 select fulltext. Strange results and
    #       text-specific search-string failures. It seem to improve as I cleaned up the code but
    #       still no clear idea of the cause of the failures, no useful error messages. Perhaps
    #       an issue with having multiple tables, one for normal search, one for fulltext search? Not sure.
    #       In desperation I tried other approaches. LIKE is fast but does not deal with punctuation.
    #       My_match() is quite a bit slower but works well. Perhaps Settings option to limit what tables
    #       are searched? No. Implemented my_match() in C, called from my_match_c(). That is faster and works great.
    #       Have not implemented ignore_words in that yet. Maybe never.

    def my_match( self, data, words ):
        data = set( re.split( '\s|\.|/|,', data.lower() ))      # Split data on space . / , chars.
        words = words.lower().split()
        for val in data:
            if val in ignore_words:     # Ignore extensions on file names.
                return False
        for word in words:
            if word not in data:
                return False
        return True                 # True only if all elements of data match all elemnts of the search string.

    # ----------------------------------------
    #   WRW 18 Feb 2022 - Implemented my_match() in C as an external module. Works great, faster than Python.
    #   This is called by Sqlite during matching when 'WHERE my_match_c( data, words )" appears in query

    def my_match_c( self, data, words ):
        try:
            return fullword.match( data, words )                                             

        except Exception as e:                                  # TESTING, no, keep, may generate exception on unexpected data length.
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on my_match_c(), type: {extype}, value: {value}", file=sys.stderr )
            print( f"  Data: {data}", file=sys.stderr  )
            print( f"  Words: {words}", file=sys.stderr  )
            return False

    # ----------------------------------------
    #   WRW 16 Feb 2022 - Include this along with create_function() in do_main() to add SELECT REGEXP support.
    #   Was slow and never fully implemented.

    def regexp( self, y, x ):
        return True if re.search(y, x) else False

    # ----------------------------------------
    #   Another implementation

    # def regexp(expr, item):
    #   reg = re.compile(expr)
    #   t = reg.search(item)
    #   if t:
    #       print( item )
    #       print( expr )
    #   return reg.search(item) is not None

    # ----------------------------------------
    #   Called from do_query...() functions in birdland.py.
    #   Return a where clause and data for parameter substitution.
    #   Function my_match_c() is called by Sqlite when matching.

    def get_fulltext( self, col, s ):
        # match_type = "simple-like"
        # match_type = "regexp"
        # match_type = "like"
        # match_type = "my_match"
        match_type = "my_match_c"

        s = s.strip()                   

        # ----------------------------------------------
        # Quoted strings match exactly for any match type.

        if( s[0] == "'" and s[-1] == "'" or
            s[0] == '"' and s[-1] == '"' ):
            w = s[1:-1]                     # Remove leading and trailing quote
            return f"{col} = ? COLLATE NOCASE", [w]

        # ----------------------------------------------
        #   This is best and fast. Same as below but in C.

        elif match_type == "my_match_c":
            return f"my_match_c( {col}, ? )", [s]

        # ----------------------------------------------
        #   This is best but a bit slow. Same as above but in Python.

        elif match_type == "my_match":
                return f"my_match( {col}, ? )", [s]

        # ----------------------------------------------
        #   This matches space-separated words.
        #       Faster than REGEXP and it works! Looks good.
        #       /// Resume - add punctuation to this?
        #   Found one-word issue with 'aparecida'.

        elif match_type == "like":
            data = []
            query = []
            for w in s.split():
                query.append( f"({col} = ? COLLATE NOCASE OR {col} LIKE ? OR {col} LIKE ? OR {col} LIKE ?)" )
                data.append( w )                    # One word title
                data.append( f"% {w}" )             # At end of line, preceeded by space
                data.append( f"{w} %" )             # At beginning of line, followed by space
                data.append( f"% {w} %" )           # In middle of line surrounded by spaces
            return ' AND '.join( query ), data

        # ----------------------------------------------
        #    This may be good if I could get it to work

        elif match_type == "regexp":
            data = []
            query = []
            for w in s.split():
                #   I couldn't get this to work. Also slower than LIKE.
                query.append( f"{col} REGEXP ?" )
                data.append( f"^{w}$|^{w}\s+|\s+{w}$|\s+{w}\s+" )
            return ' AND '.join( query ), data

        # --------------------------------------------
        #   This matches anyplace in title including within words. Not too useful.

        elif match_type == "simple-like":
            data = []
            query = []
            for w in s.split():
                query.append( f"{col} LIKE ?" )
                data.append( f"%{w}%" )             # Must put the percent signs here, not in LIKE '%?%'. No substitution inside quotes.
            return ' AND '.join( query ), data

    # ------------------------------------------------------------------------

    def set_window( self, window ):
        self.window = window

    # def set_display_keys( self, image, image_tab, page_number ):
    #     self.image_key = image
    #     self.image_tab_key = image_tab
    #     self.page_number_key = page_number

    # ------------------------------------------------------------------------
    #   add() and save() are use by source-specific routines to build
    #       data in Index.Json directory.
    #   WRW 6 Jan 2022 - Collapse multiple spaces to one in title

    def add( self, book, item ):
        item[ 'title' ] = " ".join( item[ 'title' ].split())
        item[ 'title' ] = fb_title_correction.do_correction( self.corrections_log, item[ 'title' ] )   # WRW 3 Feb 2022 - Clean up the title
        self.books.setdefault( book, [] ).append( item )

    # ------------------------------------------------------------------------

    def set_music_file( self, book, music_file ):
        if not book in self.music_files:
            self.music_files[ book ] = music_file

    # ------------------------------------------------------------------------

    def save( self, source, src ):
        # with open( self.conf.localbooknames, "w" ) as ln_fd, \
        with open( self.conf.val( 'localbooknames', source ), "w" ) as ln_fd, \
             open( Proto_Local2Canon, "w" ) as pl2c_fd, \
             open( Proto_Sheet_Offsets, "w" ) as ppo_fd,  \
             open( Proto_Canonical2File, "w" ) as pc2f_fd:

            for book in sorted( self.books ):
                print( book, file=ln_fd )
                print( f"{book} | (1, 0)", file=ppo_fd )
                print( f"{book} | {book}", file=pl2c_fd )

                if book in self.music_files:
                    music_file = self.music_files[ book ]           
                else:
                    music_file = book + ".pdf"

                print( f"{book} | {music_file}", file=pc2f_fd )

                fbook = clean_filename( book )
                ofile = f'{self.MusicIndexDir}/{src}-{fbook}.json.gz'

                book = " ".join( book.split())
                source = " ".join( source.split())

                full_contents = {
                    'local': book,
                    'source' : source,
                    'contents': self.books[ book ],
                }                             

                #   WRW 11 Feb 2022 - Compress output

                json_text = json.dumps( full_contents, indent=2 )
                with gzip.open( ofile, 'wt' ) as ofd:
                    ofd.write( json_text )

                # with open( ofile, "w" ) as ofd:
                #     ofd.write( json.dumps( full_contents, indent=2 ))

    # ------------------------------------------------------------------------
    #   WRW 7 Mar 2022 - Added save_csv() so can avoid shipping the entire buffalo.html
    #       raw source file. Huge.

    def save_csv( self, source, src, ofile ):
        with gzip.open( ofile, 'wt' ) as ofd:
        # with open( ofile, "w" ) as ofd:
            csvwriter = csv.writer( ofd )
            for book in sorted( self.books ):
                book = " ".join( book.split())
                source = " ".join( source.split())
                for content in self.books[ book ]:
                    csvwriter.writerow( [book, content['title'], content[ 'sheet' ], content['composer'], content['lyricist'] ] )

    # ------------------------------------------------------------------------
    #   Get a list of local names from Local2Canon. That is created by hand
    #       possibly starting with Proto file.
    #       WRW 23 Feb 2022 - Here getting default name for local2canon, not from config file.
    #   WRw 13 Mar 2022 - Looks like not used, add OMIT.

    def OMIT_get_local_names( self, source ):
        path = self.conf.val( 'local2canon', source )
        if os.path.isfile( path ) and os.access( path, os.R_OK):
            with open( path ) as fd:
                local2canon = fd.readlines()
            local2canon = [ x.strip() for x in local2canon ]
            local = [ x.split( '|' )[0] for x in local2canon ]
            local = [ x.strip() for x in local ]
            return local
        else:
            print( f"WARNING: {self.Local2Canon} not found", file=sys.stderr )
            return []

    # ------------------------------------------------------------------------
    #   Call 'callback' for each source file in Index.Json matching 'src'

    def get_music_index_data_by_src( self, src, callback, **kwargs ):
        curdir = os.getcwd()
        os.chdir( self.MusicIndexDir )
        files = glob.glob( f"{src}*.json.gz" )
        for file in files:
            with gzip.open( file, 'rt' ) as ifd:
            # with open( file ) as ifd:
                data = json.load( ifd )
                callback( src, data, file, **kwargs )
        os.chdir ( curdir )

    # ------------------------------------------------------------------------

    def OMIT_get_srcs( self ):
        return src2source.keys()

    # ------------------------------------------------------------------------
    #   WRW 2 Mar 2022 - Original returned array of arrays, now returns just array.

    def get_srcs( self ):
        return sorted( list( self.conf.src_to_source.keys() ) )

    # ------------------------------------------------------------------------
    #   Get list of source identifiers only for books in MusicIndexDir
    #   (pattern, repl, string, count=0, flags=0)
    #   WRW 2 Mar 2022 - This returned array of arrays, above now returns just array.
    #       Probably did this for consistency with other functions returning multiple column values.

    def OMIT_get_srcs( self ):

        txt = "SELECT DISTINCT src FROM local2canonical ORDER BY src"
        try:
            dc.execute( txt )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            return None

        else:
            res = [ [row['src']] for row in dc.fetchall() ]
            return res

    # ------------------------------------------------
    #   WRW 7 Feb 2022 - For index diff work.
    #   Get list of canonicals with more than one index source

    def get_canonicals_with_index( self ):
        txt = "SELECT canonical, local, src FROM local2canonical GROUP BY canonical HAVING COUNT( canonical )> 1 ORDER BY canonical"

        try:
            dc.execute( txt )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            return None
    
        else:
            res = [ { 'canonical': row['canonical'], 'src': row['src'], 'local': row['local'] } for row in dc.fetchall() ]
            return res

    # ------------------------------------------------

    def get_canonicals( self ):
        txt = 'SELECT canonical FROM canonicals ORDER BY canonical'

        try:
            dc.execute( txt )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            return None
    
        else:
            res = [ [row['canonical']] for row in dc.fetchall() ]
            return res

    # ------------------------------------------------

    def get_files( self, fb_flag ):
        query = 'SELECT file FROM music_files where fb_flag = %s ORDER BY file'
        data = [ fb_flag ]

        query = fix_query( query )
        try:
            dc.execute( query, data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {query}", file=sys.stderr  )
            return None
    
        else:
            res = [ [row['file']] for row in dc.fetchall() ]
            return res

    # ------------------------------------------------
    def get_local_from_canonical_src( self, canonical, src ):
        query = "SELECT local FROM local2canonical WHERE canonical = %s AND src = %s"
        query = fix_query( query )
        data = [ canonical, src ]

        try:
            dc.execute( query, data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {query}", file=sys.stderr  )
            return None
    
        else:
            row = dc.fetchone()
            res = row[ 'local' ] if row else None
            return res

    # ------------------------------------------------
    #    This is based on index files, not the database, now config file.
    #       Need both. This used by build-tables.py

    def get_srcs_from_index( self ):
        srcs = set()
        cur = os.getcwd()
        os.chdir ( self.MusicIndexDir )
        files = glob.glob( '*' )
        os.chdir ( cur )
        [ srcs.add( re.sub( '\-.*$', '', file )) for file in files ]

        return list( srcs )

    # ------------------------------------------------------------------------
    #   Get list of local names from MusicIndexDir for src
    #   (pattern, repl, string, count=0, flags=0)

    def get_locals_from_src( self, src ):

        txt = "SELECT DISTINCT local FROM local2canonical WHERE src = %s ORDER BY local"  
        txt = fix_query( txt )
        data = [src]

        try:
            dc.execute( txt, data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            print( f"  {data}", file=sys.stderr  )
            return None
    
        else:
            # res = []
            # for row in dc.fetchall():
            #     res.append( [row['local']] )

            res = [ [row['local']] for row in dc.fetchall() ]

            return res

    # ------------------------------------------------
    #   This is based on index files, not the database.
    def old_get_locals_from_src( self, src ):
        locals = set()

        cur = os.getcwd()
        os.chdir ( self.MusicIndexDir )
        files = glob.glob( f'{src}-*' )
        os.chdir ( cur )
        for file in files:
            m = re.match( f'{src}-(.*)\.json', file )
            if m:
                locals.add( m[1] )

        return list( locals )

    # ------------------------------------------------------------------------
    #   This is similar to get_table_of_contents() but returns dict, ordered by sheet, and includes composer
    #   For Index Management support.

    def get_index_from_src_local( self, src, local ):

        query = """SELECT title, sheet, composer FROM titles_distinct
                   JOIN titles USING( title_id )
                   WHERE src = %s
                   AND local = %s
                   ORDER BY sheet +0
                """
        query = fix_query( query )
        data = [src, local]
        dc.execute( query, data )

        res = [ { 'title': row[ 'title' ], 'sheet': row[ 'sheet' ], 'composer': row[ 'composer'] } for row in dc.fetchall() ]

        return res

    # --------------------------------------------------------------------------

    def old_get_index_from_src_local( self, src, local ):
        ifile = Path( self.MusicIndexDir, f"{src}-{local}.json" )
        with open( ifile ) as ifd:
            data = json.load( ifd )
            return data

    # ------------------------------------------------------------------------
    #   Translate src name (3-letter abbreviation) to full source name
    #   Do this only here, not in source-specific code.
    #   In conf:
    #       self.source_to_src[ ssource ] = src
    #       self.src_to_source[ src ] = ssource

    def get_source_from_src( self, src ):
        if src in self.conf.src_to_source:           
            return self.conf.src_to_source[ src ]
        else:
            return None

    # ------------------------------------------------------------------------
    #   Call callback for each source with data represented in Index.Json directory

    def traverse_sources( self, callback, **kwargs ):
        for src in self.get_srcs_from_index():
            callback( src, **kwargs )

    # ------------------------------------------------------------------------

    def get_title_id_from_title( self, dc, title ):

        txt = "SELECT title_id, title FROM titles_distinct WHERE title = %s"      # For testing.
        # txt = "SELECT title_id FROM titles_distinct WHERE title = %s"
        data = [title]

        txt = fix_query( txt )
        try:
            dc.execute( txt, data )
    
        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            print( f"  {data}", file=sys.stderr  )
            return None
    
        else:
            rows = dc.fetchall()
            if len(rows) > 1:
                print( f"ERROR: expected 1 row from titles_distinct, got {len(rows)}", file=sys.stderr )
                print( f"   '{title}'", file=sys.stderr  )
                for row in rows:
                    # print( row, file=sys.stderr )
                    print( f"title: '{row[ 'title' ]}', id: '{row['title_id']}'", file=sys.stderr )
                return None
    
            if len(rows) == 1:
                return rows[0]['title_id']
    
            else:
                # print( f"ERROR: no match in titles_distinct table for:", file=sys.stderr )
                # print( f"   {title}", file=sys.stderr  )
                return None

    # ------------------------------------------------------------------------
    #   Adjust the sheet number given in the index to the page number in the
    #       .pdf file. Uses data from sheet_offset table, which comes from
    #       source-specific 'Page-Offsets.txt' file.

    #   /// RESUME - is this needed? Why include title? How about just get_page_from_sheet()
    #   Call in check_pages() changed to get_page_from_sheet(). Looks like can go.
    
    def OMIT_adjust_page( self, dc, page, src, local, title, verbose ):
    
        query = """
            SELECT page + sheet_offset AS sheet
            FROM
            (
                SELECT src, local, title_id,
                MAX( sheet_start ) AS max_sheet_start
                FROM sheet_offsets
                JOIN titles USING( src, local )
                JOIN titles_distinct USING( title_id )
                WHERE
                titles.src = %s
                AND titles.local = %s
                AND titles_distinct.title = %s
                AND page >= sheet_start
                GROUP BY title_id
            ) AS subq
            JOIN titles USING( src, local, title_id )
            JOIN titles_distinct ON titles_distinct.title_id = subq.title_id
            JOIN sheet_offsets ON sheet_offsets.src = subq.src
                              AND sheet_offsets.local = subq.local
                              AND sheet_offsets.sheet_start = subq.max_sheet_start
    /*
            WHERE titles.src = %s
            AND titles.local = %s
            AND titles_distinct.title = %s
    */
            /* ORDER BY sheet +0 */
        """
    
        data = [ src, local, title, src, local, title ]
        # data = [ src, local, title ]
    
        dc.execute( query, data )
        rows = dc.fetchall()
    
        #   Someone, likely the python MySQL library is coercing sheet into float. MySql is not doing it.
        #   Needs to be string for calling PDF show program
    
        if len( rows ) == 1:
            sheet = rows[0][ 'sheet' ]
            sheet = str( int(sheet) )
    
        elif len( rows ) > 1:
            if verbose:
                print( f"ERROR: adjust_page( {page}, {src}, {local}, {title} ) failed, multiple matches", file=sys.stderr )
                for row in rows:
                    print( f"   sheet: {row[ 'sheet' ]}", file=sys.stderr )
            sheet = page
    
        else:
            if verbose:
                print( f"ERROR: adjust_page( {page}, {src}, {local}, {title} ) failed, no match", file=sys.stderr )
            sheet = None
    
        return sheet
    
    # --------------------------------------------------------------------------
    #        AND %s >= sheet_start + sheet_offset

    def get_sheet_offset( self, page, src, local ):
        query = """
            SELECT sheet_offset
            FROM sheet_offsets
            WHERE src = %s
            AND local = %s
            AND %s >= sheet_start               
            ORDER BY id DESC
            LIMIT 1
        """
        query = fix_query( query )
        data = [ src, local, page ]
        dc.execute( query, data )
        row = dc.fetchone()

        return row[ 'sheet_offset' ] if row else None

    # --------------------------------------------------------------------------
    #   Remember: 'sheet' is what is printed in the book, 'page' is the PDF page number.
    #       page  = sheet_offset + sheet
    #       sheet =  page - sheet_offset
    #   *** sheet_start - the first sheet where page = sheet_offset + sheet
    #   Returns page as a string

    #   WRW 1 Feb 2022 - Changed to return None, not page, when don't find match.
    #       Changed to do it all in SQL. Looks good.

    #   WRW 4 Feb 2022 - Change algorithm:
    #       Find last sheet_offsets entry where page >= (sheet_start + sheet_offset) ordered by sheet_start + sheet_offset
    #       Had error in earlier approach.

    def get_sheet_from_page( self, page, src, local ):

        query = """SELECT %s - sheet_offset AS sheet
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   AND %s >= sheet_start               
                   ORDER BY id DESC
                   LIMIT 1
                """
        query = fix_query( query )
        data = [page, src, local, page]
        dc.execute( query, data )

        row = dc.fetchone()
        return str(int(row[ 'sheet' ])) if row else None

    # ----------------------------------------------------------------------------
    #   Remember: 'sheet' is (should be) what is printed in the book, 'page' is the PDF page number.
    #   sheet_start: The first sheet where page = sheet_offset + sheet
    #       page = sheet_offset + sheet
    #       sheet = page - sheet_offset
    #   Returns page as a string

    #   WRW 2 Feb 2022 - Trying this in place of adjust_page(). I don't see need for
    #       title, which adjust_page() uses. Looks fine.

    #   WRW 4 Feb 2022 - Change algorithm:
    #       Find last sheets_offsets entry where sheet >= (sheet_start - sheet_offset) ordered by sheet_start + sheet_offset
    #       Had error in earlier approach.

    def get_page_from_sheet( self, sheet, src, local ):

        query = """SELECT %s + sheet_offset AS page
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   AND %s >= sheet_start
                   ORDER BY id DESC
                   LIMIT 1
                """

        query = fix_query( query )
        data = [sheet, src, local, sheet]
        dc.execute( query, data )

        # print( query )
        # print( data )

        row = dc.fetchone()
        return str(int(row[ 'page' ])) if row else None

    # ----------------------------------------------------------------------------
    def OLD_get_sheet_from_page( self, page, src, local ):

        query = """SELECT sheet_start, sheet_offset
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   ORDER BY sheet_start DESC
                """

        data = [src, local]
        dc.execute( query, data )

        page = int(page)

        for row in dc.fetchall():
            sheet_start = row[ 'sheet_start' ]
            sheet_offset = row[ 'sheet_offset' ]
            if page >= sheet_start + sheet_offset:
                sheet = page - sheet_offset
                return sheet

        return None

    # ----------------------------------------------------------------------------
    #   WRW 7 Jan 2022 - For First/Prev/Next/Last - do a higher level to update button box
    #       Show saved book with updated page. Oops, brain fart.

    # def show_music_file_saved( self, page ):
    #     t = self.save_music_file
    #     self.show_music_file( t['file'], page, t['title'], t['sheet'], t['src'], t['canonical'], t['local'], **t['kwargs'] )

    # --------------------------------------------------------------------------
    #   Get title given page number, src, and local.
    #   Interested in this to move back and forward by page and show title of new page.
    #   How reverse page offsets?
    #   /// RESUME Look at Mystery Train 111 Asp rbblues. Strange dup there.

    def get_titles_from_sheet( self, sheet, src, local ):

        query = """SELECT title FROM titles_distinct
                   JOIN titles USING( title_id )
                   WHERE sheet = %s
                   AND src = %s
                   AND local = %s
                   ORDER BY title
                """
        query = fix_query( query )
        data = [sheet, src, local]
        dc.execute( query, data )
        res = [ row[ 'title' ] for row in dc.fetchall() ]
        return res

    # --------------------------------------------------------------------------

    def get_table_of_contents( self, src, local ):

        query = """SELECT title, sheet FROM titles_distinct
                   JOIN titles USING( title_id )
                   WHERE src = %s
                   AND local = %s
                   ORDER BY title
                """
        query = fix_query( query )
        data = [src, local]
        dc.execute( query, data )

        res = [ [ row[ 'title' ], row[ 'sheet' ] ] for row in dc.fetchall() ]
        return res

    # --------------------------------------------------------------------------
    #   WRW 22 Jan 2022 - Couple of back mappings needed to get TOC from file or canonical.

    def get_canonical_from_file( self, file ):
        query = """SELECT canonical FROM canonical2file
                   WHERE file = %s
                """
        query = fix_query( query )

        data = [file]
        dc.execute( query, data )
        row = dc.fetchone()
        return row[ 'canonical' ] if row else None

    # --------------------------------------------------------------------------
    #   Get music filename from canonical
    
    def get_file_from_canonical( self, canonical ):
    
        query = """SELECT file FROM canonical2file
                   WHERE canonical = %s
                """
        query = fix_query( query )
        data = [canonical]
    
        dc.execute( query, data )
        rows = dc.fetchall()

        if len(rows) != 1:
            # print( f"ERROR: get_file_by_canonical( {canonical} ) returned {len(rows)}, expected 1", file=sys.stderr )
            # sys.exit(1)
            return None
    
        return rows[0]['file']
    
    # --------------------------------------------------------------------------

    def get_canonical_from_src_local( self, src, local ):
        query = """SELECT canonical FROM local2canonical
                   WHERE src = %s
                   AND local = %s
                """
        query = fix_query( query )
        data = [ src, local ]
        dc.execute( query, data )
        rows = dc.fetchall()

        if len(rows) != 1:
            # print( f"ERROR: get_file_by_canonical( {canonical} ) returned {len(rows)}, expected 1", file=sys.stderr )
            # sys.exit(1)
            return None
    
        return rows[0]['canonical']

    # --------------------------------------------------------------------------
    #   Note that there is a one to many relationship that will have to be disambiguated.

    def get_src_local_from_canonical( self, canonical ):

        query = """SELECT l2c.src, l2c.local FROM local2canonical l2c
                   JOIN src_priority p USING( src )
                   WHERE l2c.canonical = %s
                   ORDER BY priority
                   LIMIT 1
                """
        query = fix_query( query )
        data = [ canonical ]
        dc.execute( query, data )

        res = [ [ row[ 'src' ], row[ 'local' ]] for row in dc.fetchall() ]

        return res

    # --------------------------------------------------------------------------
    #   Query specifically to support index diff

    def get_diff_data( self, canonical ):

        query = """
            SELECT title, titles.src, local, sheet
            FROM titles
            JOIN titles_distinct USING( title_id )
            JOIN local2canonical USING( local, src )
            WHERE canonical = %s
            ORDER BY sheet+0
        """
        query = fix_query( query )
        data = [canonical]
        dc.execute( query, data )
        res = [ { 'title' : row[ 'title' ], 'src': row[ 'src' ], 'local': row[ 'local' ], 'sheet': row[ 'sheet' ] } for row in dc.fetchall() ]
        return res

    # --------------------------------------------------------------------------

    def play_audio_file( self, path ):
        self.close_youtube_file()
        self.stop_audio_file()

        if not Path( path ).is_file():                  # Likely excessive but let's be safe.
            t = f"Can't find audio file '{path}'."
            self.conf.do_popup( t )
            return

        player = self.ExternalAudioPlayer
        player = [ x for x in player.split() ]      # Convert optional args to array elements

        if not player:
            t = f"No Audio Player given in config file"
            self.conf.do_popup( t )
            return

        if shutil.which( player[0] ):
            play_cmd = [ *player, path ]
            self.audio_popen = subprocess.Popen( play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

        else:
            t = f"Audio Player given in config file '{player[0]}' not found."
            self.conf.do_popup( t )

    # --------------------------------------------------------------------------

    def play_midi_file( self, path ):
        self.close_youtube_file()
        self.stop_audio_file()

        if not Path( path ).is_file():                  # Likely excessive but let's be safe.
            t = f"Can't find midi file '{path}'."
            self.conf.do_popup( t )
            return

        player = self.ExternalMidiPlayer
        player = [ x for x in player.split() ]

        if not player:
            t = f"No Midi Player given in config file"
            self.conf.do_popup( t )
            return

        if shutil.which( player[0] ):
            play_cmd = [ *player, path ]
            self.midi_popen = subprocess.Popen( play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

        else:
            t = f"Midi Player given in config file '{player[0]}' not found."
            self.conf.do_popup( t )
            return

    # --------------------------------------------------------------------------

    def open_youtube_file( self, file ):
        self.stop_audio_file()
        self.close_youtube_file()

        open_cmd = [ 'minitube', file ]
        self.youtube_popen = subprocess.Popen( open_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

    # --------------------------------------------------------------------------

    def open_youtube_file_alt( self, yt_id ):
        self.stop_audio_file()
        self.close_youtube_file()

        url = f"https://www.youtube.com/watch?v={yt_id}"

        viewer = self.ExternalYouTubeViewer
        viewer = [ x for x in viewer.split() ]

        if not viewer:
            t = f"No YouTube Viewer given in config file"
            self.conf.do_popup( t )
            return

        if shutil.which( viewer[0] ):
            view_cmd = [ *viewer, url ]
            self.youtube_popen = subprocess.Popen( view_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

        else:
            t = f"YouTube Viewer given in config file '{viewer[0]}' not found."
            self.conf.do_popup( t )
            return

    # --------------------------------------------------------------------------

    def stop_audio_file( self ):
        if self.audio_popen:
            self.audio_popen.kill()
            self.audio_popen = None

        if self.midi_popen:
            self.midi_popen.kill()
            self.midi_popen = None

    # --------------------------------------------------------------------------

    def close_youtube_file( self ):
        if self.youtube_popen:
            self.youtube_popen.kill()
            self.youtube_popen = None

    # --------------------------------------------------------------------------
    #   os.walk( folder ) returns generator that returns list of folders and list of files
    #       in 'folder'.
    
    def listfiles( self, folder ):
        for root, folders, files in os.walk(folder):
            for file in files:
                yield (root, file)
                # yield os.path.join(root, file)

    # ----------------------------------------------------------------------------
    #   One location to set all table colors with one highlighted.
    #   De-select selected row to keep it from being reported again.
    #   18 Jan 2022 - Looks like may not be needed, perhaps bogus observation of a problem earlier?

    def OMIT_set_row_colors( self, element, len, index ):
        selected    = '#ff0000'
        background  = '#f0f0f0'
        alternating = '#d0d0ff'

        colors = [ 
            ( i, selected if i == index else ( background if (i % 2) == 0 else alternating )
            ) for i in range( 0, len )
        ]

        # element.update( select_rows=[] )
        # element.update( row_colors = colors )

    # ---------------------------------------------------
    #   PySimpleGUI has a strange behavior, bug perhaps, whereby it generates         
    #       table events when setting select on a row programmatically.
    #   safe_updat() uses some Tkinter magic to suppress the event.
    #   Thanks to Jason for this approach to suppress select event. See PySimpleGUI at github for details.

    def safe_update( self, table, values, rows=None ):

        # cur_frame = inspect.currentframe()
        # cal_frame = inspect.getouterframes(cur_frame, 2)
        # print('/// caller name:', cal_frame[1][3])

        suppress = False        # For TESTING only to demonstrate problem.
        suppress = True         # True for use, False to show problem to confirm need.

        if suppress:
            table.Widget.unbind("<<TreeviewSelect>>")                   # Disable handling for "<<TreeviewSelect>>" event

        if values and rows:
            table.update( values=values, select_rows = rows )           # It generate event "<<TreeviewSelect>>", but will be bypassed.

        elif rows:
            table.update( select_rows = rows )                          # It generate event "<<TreeviewSelect>>", but will be bypassed.

        elif values:
            table.update( values=values )                                                                          

        else:
            table.update( values=[] )

        if suppress:
            selections = table.Widget.selection()
            table.SelectedRows = [int(x) - 1 for x in selections]       # Update values['table'] for PySimpleGUI
            self.window.refresh()                                       # Event handled and bypassed
            table.Widget.bind( "<<TreeviewSelect>>", table._treeview_selected )   # Re-Enable handling for "<<TreeviewSelect>>" event

    # ---------------------------------------------------
    def log( self, event, value ):
        self.log_data.append( [event, value] )
        if len( self.log_data ) > 500:
            self.log_data.pop( 0 )

    def log_histo( self, event, value ):

        self.log_histo_data[ event ] = self.log_histo_data.setdefault( event, {} )

        if isinstance( value, str ):
            self.log_histo_data[ event ][ value ] = self.log_histo_data[ event ].setdefault( value, 0 ) + 1

        elif isinstance( value, list ):
            t = [ f"{str(x)}" for x in value ]    # value may contain ints, which cannot be joined. First convert to stt.
            t = ', '.join(t)
            t = f"[{t}]"
            self.log_histo_data[ event ][ t ] = self.log_histo_data[ event ].setdefault( t, 0 ) + 1

        elif isinstance( value, tuple ):
            t = [ f"{str(x)}" for x in value ]    # value may contain ints, which cannot be joined. First convert to stt.
            t = ', '.join(t)
            t = f"({t})"
            self.log_histo_data[ event ][ t ] = self.log_histo_data[ event ].setdefault( t, 0 ) + 1


        else:
            # print( "///", event, value, type(event), type(value ))
            self.log_histo_data[ event ][ 'unknown' ] = self.log_histo_data[ event ].setdefault( 'unknown', 0 ) + 1

    # ---------------------------------------------------
    #   WRW 8 Feb 2022 - Get all offsets for a given src/local

    def get_offsets( self, src, local ):
        query = """SELECT sheet_start, sheet_offset
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   ORDER BY sheet_start DESC
                """
        query = fix_query( query )
        data = [src, local]
        dc.execute( query, data )

        return [ { 'start': row[ 'sheet_start' ], 'offset': row[ 'sheet_offset' ] } for row in dc.fetchall() ]

    # ---------------------------------------------------

    def get_log( self ):
        return self.log_data

    def get_log_histo( self ):
        return self.log_histo_data

    def get_bl_icon( self ):
        return BL_Icon

    # ---------------------------------------------------

# ----------------------------------------------------------------------------

def continuation_lines( fd ):
    for line in fd:
        line = line.rstrip('\n')
        while line.endswith('\\'):
            line = line[:-1] + next(fd).rstrip('\n')
        yield line

# ----------------------------------------------------------------------------

if __name__ == '__main__':
    fb = FB()

    fb.set_driver( True, False, False )       # Use just MySql for this

    import fb_config
    conf = fb_config.Config()
    conf.set_driver( True, False, False )       # Use just MySql for this

    # conf.set_cwd( os.getcwd() )

    os.chdir( os.path.dirname(os.path.realpath(__file__)))  # Non-operational
    # conf.set_install_cwd( os.getcwd() )

    config = conf.get_config()              # Non-operational
    fb.set_classes( conf )
    fb.set_class_config( )

    conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
    dc = conn.cursor(MySQLdb.cursors.DictCursor)
    
    print( "srcs:", fb.get_srcs() )
    print( fb.get_title_id_from_title( dc, "Bess You Is My Woman Now" ) )
    print( fb.get_title_id_from_title( dc, "Bess You Is My Woman Now Foobar" ) )

    # --------------------------------------------------------------

    # print( fb.Music_File_Folders, fb.Music_File_Extensions, fb.Index_Sources )
    print( fb.Music_File_Folders )
    print( fb.Music_File_Root, fb.Audio_File_Root )
    print( fb.Canonicals, fb.Canonical2File, fb.YouTubeIndex )

    print( fb.Audio_Folders )

    # --------------------------------------------------------------

    for sheet in [ 526, 527, 528, 529, 530 ]:
        page = fb.get_page_from_sheet( str( sheet ), 'Skr', 'firehouse_jazzband' )
        print( f"sheet {sheet}, page: {page}" )

    print()
    for page in [ 526, 527, 528, 529, 530 ]:
        sheet = fb.get_sheet_from_page( str( page ), 'Skr', 'firehouse_jazzband' )
        print( f"page: {page}, sheet: {sheet}" )

    print()
    for page in [ 526, 527, 528, 529, 530 ]:
        offset = fb.get_sheet_offset( str( page ), 'Skr', 'firehouse_jazzband' )
        print( f"page: {page}, offset: {offset}" )

    conn.close()    # non-operational

# ----------------------------------------------------------------------------


