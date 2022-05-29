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
import configparser
import socket
import subprocess
import shutil
from pathlib import Path
import inspect
import gzip
import ctypes
import csv
import tempfile

import fb_title_correction

try:                            # WRW 3 May 2022 - in case there is a problem with fullword module in some environments.
    import fullword             # Make bogus name 'xfullword' to test missing module
    Fullword_Available = True

except ImportError as e:
  # print( "OPERATIONAL: import fullword failed, using alternative", file=sys.stderr )
    Fullword_Available = False

# ---------------------------------------------------------------------------
#   Note, some index files have 4th column with page count for title.
#   Move some to config file? No, all remaining are only used here.
#   Moved MusicIndexDir to config file and changed fakebookifile to youtube_index.

Proto_Local2Canon =     'Proto-Local2Canon.txt'
Proto_Sheet_Offsets =   'Proto-Sheet-Offsets.txt'
Proto_Canonical2File =  'Proto-Canonical2File.txt'
DocFile =               'birdland.pdf'
Create_Quick_Ref =      'birdland-create.pdf'
# BL_Icon =             'Icons/Bluebird-64.png'
BL_Icon =               'Icons/Saxophone_64.png'

ignore_words = set( ['mid', 'pdf'] )    # used in my_match()

extcmd_popen = None

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
        self.chordpro_popen = None
        self.jjazz_popen = None
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

        Show_Log = True
        Show_Log = False        # True to save log of corrections. Necessary to do it here as later logging is on clean data.

        if Show_Log:
            self.corrections_log  = open( "/tmp/Title-corrections.txt", "a" )   # Remember to clear file before each execution of birdland.py
        else:
            self.corrections_log  = None

        # ----------------------------------------

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
      # self.ShowIndexMgmtTabs =        self.conf.val('show_index_mgmt_tabs')       # WRW 28 Mar 2022 - Looks unused

        self.ExternalMusicViewer    =   self.conf.val( 'external_music_viewer' )
        self.ExternalAudioPlayer    =   self.conf.val( 'external_audio_player' )
        self.ExternalMidiPlayer    =    self.conf.val( 'external_midi_player' )
        self.ExternalYouTubeViewer =    self.conf.val( 'external_youtube_viewer' )
        self.Source_Priority =          self.conf.val('source_priority')
    
        self.MusicIndexDir =            self.conf.val('music_index_dir')

    # ------------------------------------------------------------------------
    #   Only used by add() for source-specific do_*.py, don't bother loading otherwise.
    #   WRW 14 Apr 2022 - Got broader corrections file work done. Want to include canonical
    #   in corrections file for titles corrections in case needed later.

    def load_corrections( self ):
        self.corrections = {}

        for cfile in [
                Path( self.conf.val( 'corrections' )).with_suffix( '.A.txt' ),      # Built in fb_index_diff.py
                Path( self.conf.val( 'corrections' )).with_suffix( '.B.txt' )       # Built in build_tables.py build_the_corrections_file()
            ]:

            line_counter = 0
            with open( cfile ) as fd:
                for line in fd:
                    line_counter += 1
                    cnt = line.count( '|' )
                    if cnt == 2:
                        orig, corrected, canonical = line.split( '|' )
                    elif cnt == 1:
                        orig, corrected = line.split( '|' )
                    else:
                        print( f"ERROR: Unexpected field count {cnt} on line {line_counter} in correction file {cfile.as_posix()}", file=sys.stderr )
                        sys.exit(1)

                    orig = orig.strip()
                    corrected = corrected.strip()
                    self.corrections[ orig ] = corrected

    # ----------------------------------------
    #   WRW 23 Mar 2022 - Need to save and restore dc using fb_utils from
    #   build_tables.py and diff_index.py running as modules, not separate
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
        path = Path( self.conf.val( 'documentation_dir' ), DocFile ).as_posix()
        return path

    def get_create_quick_ref( self ):
        path = Path( self.conf.val( 'documentation_dir' ), Create_Quick_Ref ).as_posix()
        return path

    def get_fullword_available( self ):
        return Fullword_Available

    # ------------------------------------------------------------------------
    #   WRW 15 Feb 2022 - An another approach to full-text matching without using Sqlite 'USING fts5()'
    #       Either I'm missing something or fulltext is not working well in Sqlite.

    #       Quoted strings match exactly.
    #       Otherwise match all words.

    #       Save, now doing parameter substitution and don't need this:
    #           s = s.replace( "'", "''" )      # Escape single quote with ''
    #           s = s.replace( '\\', '\\\\' )   # Escape backslash with \\ so don't escape single quote when at end of field.

    #   From sqlite3 documentation:
    #       The REGEXP operator is a special syntax for the regexp() user
    #       function.  No regexp() user function is defined by default and so use of
    #       the REGEXP operator will normally result in an error message.  If an
    #       application-defined SQL function named "regexp" is added at run-time, then
    #       the "X REGEXP Y" operator will be implemented as a call to "regexp(Y,X)".

    #   Experimental pseudo fullword matching attempt. This has the potential to be really cool as
    #       I can tailor it specifically to the application.

    # ----------------------------------------
    #   WRW 16 Feb 2022 - I had a lot of problems with Sqlite3 select fulltext. Strange results and
    #       text-specific, search-string failures. It seem to improve as I cleaned up the code but
    #       still no clear idea of the cause of the failures, no useful error messages. Perhaps
    #       an issue with having multiple tables, one for normal search, one for fulltext search? Not sure.
    #       In desperation I tried other approaches. LIKE is fast but does not deal with punctuation.
    #       My_match() is quite a bit slower but works well. Perhaps Settings option to limit what tables
    #       are searched? No. Implemented my_match() in C, called from my_match_c(). That is faster and works great.
    #       Have not implemented ignore_words in that yet. Maybe never.

    # ----------------------------------------
    #   Match search string 'words' against column data 'data'. Return True if match.
    #       data: filename, song title
    #       words: 'love me tender'
    #   Keep this as may want to use it for testing later.

    def my_match( self, column, value ):
        column = set( re.split( '\s|\.|/|,', column.lower() ))      # Split column on space . / , chars.
        value = value.lower().split()
        for val in column:
            if val in ignore_value:     # Ignore extensions on file names.
                return False
        for word in value:
            if word not in column:
                return False
        return True                 # True only if all elements of column match all elemnts of the search string.

    # ----------------------------------------
    #   Match search string 'value' against column data 'column'. Return True if match.
    #       data: filename, song title
    #       words: 'love me tender'

    #   WRW 18 Feb 2022 - Implemented my_match() in C as an external module. Works great, faster than Python.
    #   This is called by Sqlite during matching when 'WHERE my_match_c( column, value )" appears in query

    def my_match_c( self, column, value ):
        try:
            return fullword.match( column, value )

        except Exception as e:                                  # TESTING, no, keep, may generate exception on unexpected data length.
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on my_match_c(), type: {extype}, value: {value}", file=sys.stderr )
            print( f"  Column: {column}", file=sys.stderr  )
            print( f"  Value: {value}", file=sys.stderr  )
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
    #   Note: This ONLY used when SQLITE is True and FULLTEXT is False, which is the default case.
    #       It is never used when MYSQL is True.

    #   match_type = "simple-like"    # Select one of several approaches here. Keep if ever want to evaluate others again.
    #   match_type = "regexp"
    #   match_type = "like"
    #   match_type = "my_match"
    #   match_type = "my_match_c"

    def get_fulltext( self, col, s ):

        if Fullword_Available:          # WRW 3 May 2022 - So can proceed if problem with availability of fullword module.
            match_type = "my_match_c"
        else:
            match_type = "like"

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
        #   This matches space-separated words.
        #       Faster than REGEXP and it works! Looks good.
        #       Add punctuation to this if ever want to use it in production.
        #   Found one-word issue with 'aparecida'.
        #   Remember, LIKE is case insensitive. Hence COLLATE NOCASE only on '=' match.
        #   Don't ignore some chars on value because they are in column and can't be ignored there as
        #       is possible with fullword module. Thus, no match when special chars in column.
        #       w = re.sub( '\"|\!|\?|\(|\)', '', w )  # Ignore same chars as in fullword module.

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
        #   This is best but a bit slow. Same as above but in Python.

        elif match_type == "my_match":
                return f"my_match( {col}, ? )", [s]

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
        #   This matches any place in title including within words. Not too useful.

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
    #   WRW 3 Apr 2022 - Add title correction via corrections file.
    #   Reminder: This is called from the Index-Sources/do*.py routines to add an item
    #       from the raw index.

    def add( self, book, item ):
        title = " ".join( item[ 'title' ].split())      # Tidy up white space.
        title = fb_title_correction.do_correction( self.corrections_log, title )   # WRW 3 Feb 2022 - Clean up the title
        if title in self.corrections:                 # Add 'The' to front of some titles where others already have it
            title = self.corrections[ title ]         # and others from index diff editing.
        item[ 'title' ] = title
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
    #   Call 'callback' for each source file in Index.Json matching 'src'

    def get_music_index_data_by_src( self, src, callback, **kwargs ):
        curdir = os.getcwd()
        os.chdir( self.MusicIndexDir )
        files = glob.glob( f"{src}*.json.gz" )
        for file in files:
          # with open( file ) as ifd:
            with gzip.open( file, 'rt' ) as ifd:
                data = json.load( ifd )
                callback( src, data, file, **kwargs )
        os.chdir ( curdir )

    # ------------------------------------------------------------------------
    #   WRW 2 Mar 2022 - Original returned array of arrays, now returns just array.

    def get_srcs( self ):
        return sorted( list( self.conf.src_to_source.keys() ) )

    # ------------------------------------------------------------------------
    #   WRW 28 Apr 2022 - Get list of srcs for indexes for canonical. In order
    #       of src priority so index 0 is tops.

    def get_srcs_by_canonical( self, canonical ):
        query = """SELECT src
                    FROM local2canonical
                    JOIN src_priority USING( src )
                    WHERE canonical = %s
                    ORDER BY priority
                 """
        data = [ canonical ]
        query = fix_query( query )

        try:
            dc.execute( query, data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {query}", file=sys.stderr  )
            return None

        res = [ row['src'] for row in dc.fetchall() ]
        return res

    # ------------------------------------------------------------------------
    #   WRW 28 Apr 2022 - Need for 'browse-src-combo' default value.

    def get_priority_src( self ):
        txt = """SELECT src
                 FROM src_priority
                 ORDER BY priority
                 LIMIT 1
              """
        try:
            dc.execute( txt )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {txt}", file=sys.stderr  )
            return None

        row = dc.fetchone()
        res = row[ 'src' ] if row else None
        return res

    # ------------------------------------------------------------------------
    #   WRW 7 Feb 2022 - For index diff work.
    #   Get list of canonicals with more than one index source

    def get_canonicals_with_index( self ):
        txt = """SELECT canonical, local, src 
                 FROM local2canonical
                 GROUP BY canonical
                 HAVING COUNT( canonical )> 1
                 ORDER BY canonical
             """
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
    #   WRW 24 Apr 2022 - Added specifically for Create Index feature. Don't reuse get_canonicals_with_index() or
    #       get_canonicals(). Here join with file as can't create index without a music file.
    #   WRW 25 Apr 2022 - Always include 'Usr' files for 'No-Index' as we may want to edit them after they were added to database.

    def get_canonicals_for_create( self, select ):
        if select == 'All':
            txt = """SELECT DISTINCT canonicals.canonical
                     FROM canonicals
                     JOIN canonical2file USING( canonical )
                     ORDER BY canonicals.canonical
                 """

        elif select == 'No-Index':                              # This is default and only useful option.
            txt = """SELECT DISTINCT canonicals.canonical
                     FROM canonicals
                     JOIN canonical2file USING( canonical )
                     LEFT JOIN local2canonical USING( canonical )
                     WHERE (local2canonical.canonical IS NULL) OR
                     (local2canonical.src = 'Usr')
                     ORDER BY canonicals.canonical
                 """

        elif select == 'Only-Index':
            txt = """SELECT DISTINCT canonicals.canonical
                     FROM canonicals
                     JOIN canonical2file USING( canonical )
                     LEFT JOIN local2canonical USING( canonical )
                     WHERE local2canonical.canonical IS NOT NULL
                     ORDER BY canonicals.canonical
                 """
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
    #   WRW 1 Apr 2022 - For editing raw index sources

    def get_raw_file( self, title, local, src ):
        query = """SELECT file, line FROM raw_index
                   JOIN titles_distinct USING( title_id )
                   WHERE title = %s AND src = %s AND local = %s
                """
        query = fix_query( query )
        data = [ title, src, local ]

        try:
            dc.execute( query, data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on SELECT, type: {extype}, value: {value}", file=sys.stderr )
            print( f"  {query}", file=sys.stderr  )
            return None
    
        else:
            row = dc.fetchone()
            file = row[ 'file' ] if row else None
            line = row[ 'line' ] if row else None
            return file, line

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
    #        AND %s >= sheet_start + sheet_offset
    #        AND %s >= sheet_start   
    #   WRW 28 Apr 2022 - This is not working with sqlite3 as it should
    #   WRW change ORDER BY id to ORDER BY offset_id. Can't do much with id in sqlite3.
    #   WRW 1 May 2022 - Realized not working. Added '+ sheet_offset' to 'AND %s >= sheet_start + sheet_offset'

    def get_sheet_offset_from_page( self, page, src, local ):
        query = """
            SELECT sheet_offset
            FROM sheet_offsets
            WHERE src = %s
            AND local = %s
            AND %s >= sheet_start + sheet_offset
            ORDER BY offset_id DESC
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
    #   WRW 1 May 2022 - Realized not working. Added '+ sheet_offset' to 'AND %s >= sheet_start + sheet_offset'

    def get_sheet_from_page( self, page, src, local ):

        query = """SELECT %s - sheet_offset AS sheet
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   AND %s >= sheet_start + sheet_offset
                   ORDER BY offset_id DESC
                   LIMIT 1
                """
        query = fix_query( query )
        data = [page, src, local, page]
        dc.execute( query, data )

        row = dc.fetchone()
        return str(int(row[ 'sheet' ])) if row else None

    # ----------------------------------------------------------------------------

    def OLD_get_sheet_from_page( self, page, src, local ):

        query = """SELECT %s - sheet_offset AS sheet
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   AND %s >= sheet_start               
                   ORDER BY offset_id DESC
                   LIMIT 1
                """
        query = fix_query( query )
        data = [page, src, local, page]
        dc.execute( query, data )

        row = dc.fetchone()
        return str(int(row[ 'sheet' ])) if row else None

    # ----------------------------------------------------------------------------

    def OLDER_get_sheet_from_page( self, page, src, local ):

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

    #   WRW 5 Apr 2022 - I don't think this is working, always returns same value. Showed up in scatter plot
    #       of page vs sheet. Problem is with Sqlite, OK with MySql. Prob is use of primary key 'id'. Add
    #       a separate id value in table as offset_id. Solved problem

    def get_page_from_sheet( self, sheet, src, local ):

        query = """SELECT %s + sheet_offset AS page
                   FROM sheet_offsets
                   WHERE src = %s
                   AND local = %s
                   AND %s >= sheet_start
                   ORDER BY offset_id DESC
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
    #   WRW 7 Jan 2022 - For First/Prev/Next/Last - do a higher level to update button box
    #       Show saved book with updated page. Oops, brain fart.

    # def show_music_file_saved( self, page ):
    #     t = self.save_music_file
    #     self.show_music_file( t['file'], page, t['title'], t['sheet'], t['src'], t['canonical'], t['local'], **t['kwargs'] )

    # --------------------------------------------------------------------------
    #   Get title given sheet number, src, and local.
    #   Need this to move back and forward by page and show title of new page.
    #   How reverse page offsets?

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
    #   WRW 29 Apr 2022 - switch from sheet to page

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
    #   Note that there is a one to many relationship that is disambiguated
    #       with join to src_priority and LIMIT 1

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

    def get_local_from_src_canonical( self, src, canonical ):

        query = """SELECT l2c.local FROM local2canonical l2c
                   WHERE l2c.src = %s AND
                   l2c.canonical = %s    
                   LIMIT 1
                """
        query = fix_query( query )
        data = [ src, canonical ]
        dc.execute( query, data )
        row = dc.fetchone()
        return row[ 'local' ] if row else None

    # --------------------------------------------------------------------------
    #   Query specifically to support index diff
    #   Get all titles for canonical from all index srcs

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
    #   Code here to kill jjazz_popen but it does not appear to be working.

    def show_jjazz_file( self, path ):
        self.close_youtube_file()
        self.stop_audio_file()

        if not Path( path ).is_file():                  # Likely excessive but let's be safe.
            t = f"Can't find jjazz file '{path}'."
            self.conf.do_popup( t )
            return

        jjazzlab = 'jjazzlab'                           # Must be in path.

        if shutil.which( jjazzlab ):
            jjazzlab_cmd = [ jjazzlab, path ]
            self.jjazz_popen = subprocess.Popen( jjazzlab_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

        else:
            t = f"JJazzLab command'{jjazzlab}' not found."
            self.conf.do_popup( t )
            return

    # --------------------------------------------------------------------------
    #   WRW 27 Apr 2022 - This is a bit exploratory, right I'm now not sure the best way to
    #       convert a chordpro file to image but the chordpro command seems like a good choice.
    #       Another option is to convert all in a batch first and just load one here.
    #       After using it briefly it looks pretty good just as is.

    def show_chordpro_file( self, path, callback ):

        if not Path( path ).is_file():                  # Likely excessive but let's be safe.
            t = f"Can't find chordpro file '{path}'."
            self.conf.do_popup( t )
            return

        chordpro = 'chordpro'
        tfile = tempfile.mkstemp()[1]           # Temp pdf file for chordpro output

        if shutil.which( chordpro ):
            chordpro_cmd = [ chordpro, '-o', tfile, path.as_posix() ]      # Must be in path.
            self.chordpro_popen = subprocess.Popen( chordpro_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )
            self.chordpro_popen.wait()      # Wait till chordpro done and have pdf file.
            callback( tfile )       # Call back to birdland.py so don't have to have pdf and meta classes here just for this.
            os.remove( tfile )

        else:
            t = f"ChordPro command'{chordpro}' not found."
            self.conf.do_popup( t )
            return

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

        if self.jjazz_popen:
            self.jjazz_popen.kill()
            self.jjazz_popen = None

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

    # --------------------------------------------------------------------------
    #   WRW 27 Mar 2022 - Move from birdland.py into here so can call from fb_config.py
    #       for some initialization
    #   Used only for bl-build-tables (build_tables.py) and bl-diff-index.

    #   run_external_command( command ) - Original, include success/error reporting.
    #   run_external_command_quiet( command ) - Same without success/error reporting, for initialization.

    def run_external_command( self, command ):

        self.window[ 'tab-results-text' ].select()
        self.window[ 'results-text' ].update( value='' )
        self.window[ 'tab-results-text'].update( visible = True )

        rcode = self.run_external_command_quiet( command, self.window[ 'results-text' ], False )

        if rcode:
            self.window['results-text' ].print( f"\nCommand failed, { ' '.join( command )} returned exit code: {rcode}" )
        else:
            self.window['results-text' ].print( f"\nCommand completed successfully." )

    # ------------------------------------

    def run_external_command_quiet( self, command, res_win, rerouted ):
        global extcmd_popen
    
        # --------------------------------------------------------------------------
        #   WRW 15 Mar 2022 - Add support for running command as included package.
        #       Can make Command_as_Module conditional on packaging type conf.Package_Type
        #       but I see no reason to do so.

        #   WRW 28 May 2022 - With support for self-contained packages suspended/removed no longer
        #       a need to run as module and a slight risk of doing so. Run as external command only.

        #   WRW 29 May 2022 - After a lot of time invested in support for the self-contained packages I
        #       decided not to use them for now and probably for ever. They are huge and no real benefit
        #       other than simplicity. Back off from that now. Command_as_Module is now False.
    
        Command_as_Module = True
        Command_as_Module = False
    
        #   Debugging = True - Sends output to stdout/stderr instead of to window.
        #       Needed to see error messages when application crashes.
    
        Debugging = True
        Debugging = False
    
        # --------------------------------------------------------------------------
        #   Run command as loadable module.
        #   click() in build_tables.py and diff_index.py is exiting, not
        #       returning back to program calling main().
        #       Work around by surrounding call with try/except SystemExit to catch exit.
        #   See: https://stackoverflow.com/questions/52740295/how-to-not-exit-a-click-cli
        #   WRW 22 Mar 2022 - Remove try/except SystemExit on call build_tables and diff_index.
        #       Confirmed click() was exiting.
        #       Added 'standalone_mode=False' to do_main() call in commands. Confirmed click()
        #       was not exiting. Problem solved. Now picking up rcode.

        #   WRW 18 May 2022 - A major failure here after upgrade PySimpleGUI from 4.57 to 4.60
        #       With reroute_stdout_to_here() bl-build-tables (build_tables.py) appears to hang
        #       at first print(). See comments in fb_config.py above build_database().
        #       I commented out Multiline( 'echo_stdout_stderr' ) and calling reroute here selectively.
    
        if Command_as_Module:
    
            if not Debugging and not rerouted:
                res_win.reroute_stdout_to_here()                # WRW 18 May 2022 - Major failure with this called for build_database().
                res_win.reroute_stderr_to_here()
    
            if command[0] == 'bl-build-tables':
                import build_tables
                rcode = build_tables.aux_main( command )
    
            elif command[0] == 'bl-diff-index':
                import diff_index
                rcode = diff_index.aux_main( command )
    
            else:
                print( f"ERROR-DEV: Unexpected command at run_external_command_quiet(): {command[0]}" )
                sys.exit(1)

            if not Debugging and not rerouted:
                res_win.restore_stdout()
                res_win.restore_stderr()

            return rcode

        # --------------------------------------------------------------------------
        #   Run command as external process.
    
        else:
            if extcmd_popen:
                extcmd_popen.kill()
                extcmd_popen = None
    
            extcmd_popen = subprocess.Popen( command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True )
            for line in extcmd_popen.stdout:
                res_win.print( line, end='' )
    
            extcmd_popen.stdout.close()
            rcode = extcmd_popen.wait()
            return rcode

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
    conf.get_config()
    conf.set_driver( True, False, False )       # Use just MySql for this
    conf.set_class_variables()

    # conf.set_cwd( os.getcwd() )

    os.chdir( os.path.dirname(os.path.realpath(__file__)))  # Non-operational
    # conf.set_install_cwd( os.getcwd() )

    conf.get_config()              # Non-operational
    fb.set_classes( conf )
    fb.set_class_config( )

    import MySQLdb
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
        offset = fb.get_sheet_offset_from_page( page, 'Skr', 'firehouse_jazzband' )
        print( f"page: {page}, offset: {offset}" )

    print()
    print('-'*60)
    print( "get_page_from_sheet()" )
    for sheet in range( 1, 20 ):
        page = fb.get_page_from_sheet( str( sheet ), 'Shr', 'Standards Real Book' )
        print( f"sheet {sheet} -> page: {page}" )

    print()
    print( "get_sheet_from_page()" )
    for page in range( 1, 30 ):
        sheet = fb.get_sheet_from_page( page, 'Shr', 'Standards Real Book' )
        print( f"page: {page} -> sheet: {sheet}" )

    print()
    print( "get_sheet_offset_from_page()" )
    for page in range( 1, 30 ):
        offset = fb.get_sheet_offset_from_page( page, 'Shr', 'Standards Real Book' )
        print( f"page: {page} -> offset: {offset}" )

    rows = fb.get_local_from_src_canonical( 'Shr', 'Standards Real Book - Chuck Sher' )
    print( rows )

    conn.close()    # non-operational

# ----------------------------------------------------------------------------


