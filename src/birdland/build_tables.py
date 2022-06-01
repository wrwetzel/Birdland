#!/usr/bin/python
# --------------------------------------------------------------------------
#   build-tables.py - build fakebook index database

#   wrw 15 Dec 2021 - this is result of work for past couple of weeks
#       resuming work started in 2020.

#   WRW 30 Dec 2021 - I had a serious bug. title_id was varchar in one table, unsigned int in another
#       Drastically slowed down searches. Corrected, OK now.

#   WRW 5 Jan 2022 - Must de-duplicate Buffalo results

#   WRW 12 Feb 2022 - Addition of sqlite. Move all DROP and index creation into table-specific code.
#       Add options for each table.

#   Spent a few minutes trying sqlite3, not a trivial drop-in.
#   Probably best to invest the time into SqlAlchemy and let do the work.
#   Not so sure after looking at Peewee ORM.
#   WRW 13 Feb 2022 - Back to looking at sqlite3

# --------------------------------------------------------------------------

import os
import sys
import json
import re
import click
import fitz
from collections import OrderedDict
from pathlib import Path
import gzip
import sqlite3
import inspect
import mutagen
import subprocess
import Levenshtein
import fb_config
import fb_utils
import fb_title_correction
import fb_pdf
import fb_metadata

# --------------------------------------------------------------------------

Old_Dc = None

# --------------------------------------------------------------------------

audio_file_extensions = [ ".mp3", ".fla", ".flac", ".FLAC", ".Mp3", ".MP3", ".mpc", ".ape", ".ogg", ".FLAC", ".wav", ".aif" ]

# ==========================================================================

def fix_query( query ):
    if SQLITE:
        query = query.replace( '%s', '?' )
    return query

# ---------------------------------------------------------------------------
#   WRW 15 Feb 2022 - Finally, put the error reporting in just one place.
#       Will now use try/execpt for all execute() calls, not just ones
#       where it was explicitly coded.

def execute( cur, txt, data=None ):
    try:
        if data:
            cur.execute( txt, data )
        else:
            cur.execute( txt )

    except Exception as e:
        all_frames = inspect.stack()
        caller_frame = all_frames[1]
        caller_file = caller_frame[1]
        caller_line = caller_frame[2]
        caller_name = caller_frame[3]

        (extype, value, traceback) = sys.exc_info()
        print( f"ERROR on execute(), type: {extype}, value: {value}", file=sys.stderr, flush=True )
        print( f"  Txt: {txt}", file=sys.stderr, flush=True    )
        if data:
            print( f"  Data: {data}", file=sys.stderr, flush=True   )
        print( f"  Called from: {caller_name}, line: {caller_line}", file=sys.stderr, flush=True  )

# ==========================================================================

def old_get_title_tag( file ):
# import audio_metadata
    try:
        metadata = audio_metadata.load( file )

    except:
        (type, value, traceback) = sys.exc_info()
        print( "ERROR: audio_metadata.load() failed", file=sys.stderr, flush=True   )
        print( "  File:", file, file=sys.stderr, flush=True   )
        print( "  Type:", type, file=sys.stderr, flush=True   )
        print( "  Value:", value, file=sys.stderr, flush=True   )
        print( "", file=sys.stderr, flush=True  )
        return None

    title = metadata.tags.title[0]
    return title

# -----------------------------------------------------------------------
# for key in metadata:
#     if key != 'APIC:' and key != 'covr' and key != 'MCDI':
#         print( "'%s' %s" %( key, metadata[ key ]), file=sys.stderr )

def get_title_tag( file ):
    title = artist = album = None

    try:
        metadata = mutagen.File( file )

    except:
        (failtype, value, traceback) = sys.exc_info()
        print( "ERROR: mutagen.File() failed", file=sys.stderr, flush=True   )
        print( "  File:", file, file=sys.stderr, flush=True   )
        print( "  Type:", failtype, file=sys.stderr, flush=True   )
        print( "  Value:", value, file=sys.stderr, flush=True   )
        print( "" )
        return (title, artist, album )

    if metadata:
        # --------------------------------------------------------------------------
        if 'title' in metadata:
            t = metadata[ 'title' ]     # Sometimes an array of array

            if isinstance( t[0], list):
                title = metadata[ 'title'][0][0]
            else:
                title = metadata[ 'title'][0]

        elif 'TIT2' in metadata:
            title = str( metadata[ 'TIT2' ] )

        else:
            print( "ERROR: 'title' or 'TIT2' not found:", file, file=sys.stderr, flush=True   )

        # --------------------------------------------------------------------------
        if 'artist' in metadata:
            t = metadata[ 'artist' ]     # Sometimes an array of array

            if isinstance( t[0], list):
                artist = metadata[ 'artist'][0][0]
            else:
                artist = metadata[ 'artist'][0]

        elif 'TPE1' in metadata:
            artist = str( metadata[ 'TPE1' ] )

        else:
            print( "ERROR: 'artist' or 'TPE1' not found:", file, file=sys.stderr, flush=True   )

        # --------------------------------------------------------------------------
        if 'album' in metadata:
            t = metadata[ 'album' ]     # Sometimes an array of array

            if isinstance( t[0], list):
                album = metadata[ 'album'][0][0]
            else:
                album = metadata[ 'album'][0]

        elif 'TALB' in metadata:
            album = str( metadata[ 'TALB' ] )

        else:
            print( "ERROR: 'album' or 'TALB' not found:", file, file=sys.stderr, flush=True   )

        # --------------------------------------------------------------------------

        return( title, artist, album )

    # --------------------------------------------------------------------------
    else:
        print( "ERROR: mutagen.File() returned None:", file, file=sys.stderr, flush=True   )
        return (title, album, artist)

# -----------------------------------------------------------------------
#   Remember, yield preserves state and resumes where left off on next call.

def listfiles(folder):
    for root, folders, files in os.walk(folder):
        for file in files:
            yield os.path.join(root, file)

# -----------------------------------------------------------------------
#   WRW 2 Mar 2022 - Build a list of all music files, that is .pdf files under
#       the music root and specified folders. Exploratory only. Not used in production

def do_scan_music_files():
    print( "\nScanning music library:", file=sys.stderr, flush=True  )

    # conf.v.music_file_extensions
    music_folders = [ x for x in conf.v.music_file_folders.split('\n') ]
    fakebook_folders = [ x for x in conf.v.c2f_editable_music_folders.split('\n') ]

    root = conf.v.music_file_root
    for folder in music_folders:
        print( folder )
        if folder in fakebook_folders:
            for file in Path( root, folder ).expanduser().glob( '**/*.[pP][dD][fF]' ):
                pass
                print( file.name )

    return 0

# -----------------------------------------------------------------------

def do_scan_audio_files():
    print( "\nScanning audio library:", file=sys.stderr, flush=True  )

    table = []

    error_count = 0
    error_count_by_extension = {}

    insert_error_count = 0
    insert_error_count_by_extension = {}

    ignore_count = 0
    ignore_count_by_extension = {}

    title_count = 0
    title_count_by_extension = {}

    # audio_folders = [ x for x in conf.v.audio_folders.split( '\n' ) ]
    audio_folders = conf.val( 'audio_folders' )

    for path in audio_folders:
        print( f"  {path}", file=sys.stderr, flush=True  )

        root = conf.val( 'audio_file_root' )
        full_path = Path( root, path ).expanduser().as_posix()
    
        for file in listfiles( full_path ):
            ext = Path( file ).suffix
            rel_path = Path( file ).relative_to( root ).as_posix()

            if ext in audio_file_extensions:
                ( title, artist, album ) = get_title_tag( file )

                # -------------------------------------------------------------
                #   WRW 19 Feb 2022 - Trying to track down a couple of funnies in audio_files table
                #       Two problems: title, artist, album could all be None.        
                #       Changed fullword_match to acccept Null.
                #       A few items have '\x00' in them in the vicinity of an ampersand. Deal with that
                #       when doing the INSERT, not here as this takes a long time to run.

                if title:
                    table.append( { 'title' : title, 'artist' : artist, 'album' : album, 'file' : rel_path } )
                    title_count += 1
                    title_count_by_extension[ext] = title_count_by_extension.setdefault( ext, 0 ) + 1
                else:
                    error_count += 1
                    error_count_by_extension[ext] = error_count_by_extension.setdefault( ext, 0 ) + 1

            else:
                ignore_count += 1
                ignore_count_by_extension[ext] = ignore_count_by_extension.setdefault( ext, 0 ) + 1
    
    # ------------------------------------------
    #   Do we want to save to a location specified on command line? Have not seen need.

    full_contents = {
        'audio_files' : table
    }

    ofile = conf.val( 'audiofile_index' )
    json_text = json.dumps( full_contents, indent=2 )
    with gzip.open( ofile, 'wt' ) as ofd:
        ofd.write( json_text )

    # ------------------------------------------

    print( "" )
    print( "Titles saved:", title_count )
    for k in OrderedDict(sorted(title_count_by_extension.items(), key=lambda x : x[1], reverse=True )):
        print( "%s: %d" % ( k, title_count_by_extension[k] ) )

    print( "" )
    print( "Extensions ignored:", ignore_count )
    for k in OrderedDict(sorted(ignore_count_by_extension.items(), key=lambda x : x[1], reverse=True )):
        print( "%s: %d" % ( k, ignore_count_by_extension[k] ) )

    print( "" )
    print( "Files with tag errors:", error_count )
    for k in OrderedDict(sorted(error_count_by_extension.items(), key=lambda x : x[1], reverse=True )):
        print( "%s: %d" % ( k, error_count_by_extension[k] ) )

    print( "" )
    print( "Files with insert errors:", insert_error_count )
    for k in OrderedDict(sorted(insert_error_count_by_extension.items(), key=lambda x : x[1], reverse=True )):
        print( "%s: %d" % ( k, insert_error_count_by_extension[k] ) )

    return 0

# -----------------------------------------------------------------------
#   WRW 19 Feb 2022 - '\x00' in strings screwing up call to my fullword_match code.
#       In the only place I saw them look they should be an ampersand.

def check_null( s ):
    if not s:
        return s

    if '\x00' in s:
        s = ' & '.join( s.split( '\x00' ) )
        print( f"NOTE: Replaced null in '{s}' with ampersand", file=sys.stderr, flush=True  )
        return s

    else:
        return s

# -----------------------------------------------------------------------
#   WRW 30 Apr 2022 - Build a table mapping file name to page count

def build_page_count( dc, c, conn ):
    txt = 'DROP TABLE IF EXISTS page_count;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS audio_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE page_count (
            id INT UNSIGNED AUTO_INCREMENT,
            file VARCHAR(255),
            page_count INTEGER,
            PRIMARY KEY(id) )
            ENGINE = MYISAM
            CHARACTER SET 'utf8mb4'
            """
        execute( c, txt )

    if SQLITE:
        txt = """CREATE TABLE page_count (
            file VARCHAR(255),
            page_count INTEGER,
            id INT AUTO_INCREMENT,
            PRIMARY KEY(id) )
            """
        execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE audio_files_fts USING fts5(
            file,
            page_count UNINDEXED,
            content='page_count',
            content_rowid='id'
            )
            """
        execute( c, txt )

    # ----------------------------------------------------------------

    txt = "SELECT file FROM canonical2file ORDER BY file"
    execute( dc, txt )
    rows = dc.fetchall()
    root = conf.val( 'music_file_root' )

    if rows:
        for row in rows:                    # Build array of all titles
            row[ 'file' ]
            path = Path( root, row['file' ] )
            doc = fitz.open( path )

            txt = "INSERT INTO page_count (file, page_count) VALUES( %s, %s )"
            data = [ row[ 'file' ], doc.page_count ]
            txt = fix_query( txt )      # Replaces %s with ? for SQLITE FULLTEXT

            execute( c, txt, data )

    if MYSQL:
        txt = 'ALTER TABLE page_count ADD FULLTEXT( file )'
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX page_count_index ON page_count( file )"
        execute( c, txt )

    return 0

# -----------------------------------------------------------------------
#   WRW 19 Feb 2022 - Check and clean up '\x00' in fields before inserting into table.

def build_audio_files( c ):
    print( "\nBuilding audio_files", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS audio_files;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS audio_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE audio_files (
            id INT UNSIGNED AUTO_INCREMENT,
            title VARCHAR(255),
            artist VARCHAR(255),
            album VARCHAR(255),
            file VARCHAR(255),
            PRIMARY KEY(id) )
            ENGINE = MYISAM
            CHARACTER SET 'utf8mb4'
            """
        execute( c, txt )

    if SQLITE:
        txt = """CREATE TABLE audio_files (
            title VARCHAR(255),
            artist VARCHAR(255),
            album VARCHAR(255),
            file VARCHAR(255),
            id INT AUTO_INCREMENT,
            PRIMARY KEY(id) )
            """
        execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE audio_files_fts USING fts5(
            title,
            artist,
            album,
            file UNINDEXED,
            content='audio_files',
            content_rowid='id'
            )
            """
        execute( c, txt )

    # -----------------------------------------------------------------------

    # ifile = Path( conf.confdir, conf.v.audiofile_index )
    ifile = conf.val( 'audiofile_index' )
    with gzip.open( ifile, 'rt') as ifd:
        audio_data = json.load( ifd )

    audio_file_count = 0
    for item in audio_data[ 'audio_files' ]:
        audio_file_count += 1
        title = item[ 'title' ]
        artist = item[ 'artist' ]
        album = item[ 'album' ]
        file = item[ 'file' ]

        title = check_null( title )
        artist = check_null( artist )
        album = check_null( album )         # Don't check file, can't modify that from what found on disk.

        data = ( [ title, artist, album, file ] )

        txt   = """INSERT INTO audio_files ( title, artist, album, file )
                VALUES( %s, %s, %s, %s )
                """
        txt = fix_query( txt )      # Replaces %s with ? for SQLITE FULLTEXT
        execute( c, txt, data )

        if FULLTEXT and SQLITE:
            txt   = """INSERT INTO audio_files_fts ( title, artist, album, file )
                    VALUES( ?, ?, ?, ? )
                    """
            execute( c, txt, data )

    # -----------------------------------------------------------------------

    if MYSQL:
        txt = 'ALTER TABLE audio_files ADD FULLTEXT( title ), ADD FULLTEXT( artist ), ADD FULLTEXT( album );'
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX audio_files_index ON audio_files( title, artist, album )"
        execute( c, txt )

    print( f"   Audio files total: {audio_file_count}", file=sys.stderr, flush=True  )

    return 0

# -----------------------------------------------------------------------
#   Read from MySql DB (only, never Sqlite3), write to audio file index compressed json file.

def do_extract_audio_data( dc ):
    table = []

    query = f"""
        SELECT title, artist, album, file
        FROM audio_files
    """
    execute( dc, query )
    rows = dc.fetchall()
    if rows:
        for row in rows:
            title = row[ 'title' ]
            artist = row[ 'artist' ]
            album = row[ 'album' ]
            file = row[ 'file' ]

            table.append( { 'title' : title, 'artist' : artist, 'album' : album, 'file' : file } )

    full_contents = {
        'audio_files' : table
    }

    # ofile = Path( conf.confdir, conf.v.audiofile_index )
    ofile = conf.val( 'audiofile_index' )

    json_text = json.dumps( full_contents, indent=2 )
    with gzip.open( ofile, 'wt' ) as ofd:
        ofd.write( json_text )

# ==========================================================================

def build_source_priority( c, conn ):
    print( "\nBuilding src_priority", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS src_priority;'
    execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE src_priority (
                src VARCHAR(255),
                priority VARCHAR(255),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY( id ) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
              """
    if SQLITE:
        txt = """CREATE TABLE src_priority (
                src VARCHAR(255),
                priority VARCHAR(255),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY( id ) )
              """
    execute( c, txt )

    priority = 1

    for src in fb.Source_Priority:
        data = [ src, priority ]
        txt = 'INSERT INTO src_priority ( src, priority ) VALUES( %s, %s )'
        txt = fix_query( txt )
        execute( c, txt, data )
        priority += 1

    if MYSQL:
        txt = "ALTER TABLE src_priority ADD INDEX( src )"

    if SQLITE:
        txt = "CREATE INDEX src_priority_index ON src_priority( src )"

    execute( c, txt )
    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   Make table of canonical book names from CanonicalNames.txt file.
#   WRW 9 Apr 2022 - Add priority and page_of_sheet_1

def build_canonicals( c, conn ):
    print( "\nBuilding canonicals", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS canonicals;'
    execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE canonicals (
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                canonical VARCHAR(255),
                page_of_sheet_1 VARCHAR(255),
                priority VARCHAR(255),
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
              """
    if SQLITE:
        txt = """CREATE TABLE canonicals (
                id MEDIUMINT AUTO_INCREMENT,
                canonical VARCHAR(255),
                page_of_sheet_1 VARCHAR(255),
                priority VARCHAR(255),
                PRIMARY KEY(id) )
              """
    execute( c, txt )

    # ---------------------------------------------

    with open( fb.Canonicals ) as fd:
        for line in fd:
            line = line.strip()
            if line:                                # Ignore blank lines
                if line.startswith( '#' ):          # Ignore comments
                    continue

                priority, page_of_sheet_1, canonical = line.split( '|' )
                priority = priority.strip()                     # Remove leading/trailing spaces,
                priority = '999' if priority == '-' else priority

                page_of_sheet_1 = page_of_sheet_1.strip()
                canonical = canonical.strip()

                data = [ priority, page_of_sheet_1, canonical ]
                txt = 'INSERT INTO canonicals ( priority, page_of_sheet_1, canonical ) VALUES( %s, %s, %s )'
                txt = fix_query( txt )

                execute( c, txt, data )

    # ---------------------------------------------

    conn.commit()
    return 0

# ----------------------------------------------------------------------------------
#   Make table from Canonical2File.txt, which was created by hand.
#   Maps canonical book name to .pdf (possibly other) file containing book.

def build_canonical2file( c, conn ):
    print( "\nBuilding canonical2file", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS canonical2file;'
    execute( c, txt )

    if MYSQL:
        txt =  """CREATE TABLE canonical2file (
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                canonical VARCHAR(255),
                file VARCHAR(255),
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
                """
    if SQLITE:
        txt =  """CREATE TABLE canonical2file (
                id MEDIUMINT AUTO_INCREMENT,
                canonical VARCHAR(255),
                file VARCHAR(255),
                PRIMARY KEY(id) )
                """
    execute( c, txt )

    # ---------------------------------------------

    # for canonical2file in fb.Canonical2File.split('\n'):
    for canonical2file in fb.Canonical2File:
        with open( canonical2file ) as fd:
            for line in fd:
                line = line.strip()
                canonical, file = line.split( '|' )
                canonical = canonical.strip()
                file = file.strip()
                if canonical and file:
                    data = ( canonical, file )
                    txt = 'INSERT INTO canonical2file ( canonical, file ) VALUES( %s, %s )'
                    txt = fix_query( txt )
                    execute( c, txt, data )

    # ----------------------

    if MYSQL:
        txt = "ALTER TABLE canonical2file ADD INDEX( canonical ), ADD INDEX( file )"

    if SQLITE:
        txt = "CREATE INDEX canonical2file_index ON canonical2file( canonical, file )"

    execute( c, txt )
    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   Make translation table between local (source-specific) book name and canonical book name.

def build_local2canonical( c, conn ):
    print( "\nBuilding local2canonical", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS local2canonical;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS local2canonical_fts;'
        execute( c, txt )

    if MYSQL:
        txt =  """CREATE TABLE local2canonical (
               canonical VARCHAR(255),
               src VARCHAR(255),
               local VARCHAR(255),
               id MEDIUMINT UNSIGNED AUTO_INCREMENT,
               PRIMARY KEY(id) )
               ENGINE = MYISAM
               CHARACTER SET 'utf8mb4'
               """
    if SQLITE:
        txt =  """CREATE TABLE local2canonical (
               canonical VARCHAR(255),
               src VARCHAR(255),
               local VARCHAR(255),
               id MEDIUMINT AUTO_INCREMENT,
               PRIMARY KEY(id) )
               """

    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE local2canonical_fts USING fts5(
            canonical,
            src UNINDEXED,
            local UNINDEXED,
            content='local2canonical',
            content_rowid='id'
        )
        """
        execute( c, txt )

    fb.traverse_sources( int_build_local2canonical, c=c )

    if MYSQL:
        txt = "ALTER TABLE local2canonical ADD INDEX( src ), ADD INDEX( local ), ADD INDEX( canonical )"
        execute( c, txt )

        txt = "ALTER TABLE local2canonical ADD FULLTEXT( canonical )"
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX local2canonical_index ON local2canonical( src, local, canonical )"
        execute( c, txt )

    conn.commit()
    return 0

# --------------------------------------------------------------------------

def int_build_local2canonical( src, **kwargs ):
    c = kwargs[ 'c' ]

    # ifile = os.path.join( "..", "Index-Sources", fb.get_source_from_src( src ), fb.Local2Canon )
    source = fb.get_source_from_src( src )

    ifile = conf.val( 'local2canon', source )
    # ifile = Path( conf.get_source_path( source ), conf.val( 'local2canon', source ))

    with open( ifile ) as fd:
        for line in fd:
            line = line.strip()
            local, canonical = line.split( '|' )
            local=local.strip()
            canonical=canonical.strip()

            if local and canonical:
                data = ( src, local, canonical )
                txt = 'INSERT INTO local2canonical ( src, local, canonical ) VALUES( %s, %s, %s )'
                txt = fix_query( txt )
                execute( c, txt, data )

                if FULLTEXT and SQLITE:
                    txt = 'INSERT INTO local2canonical_fts ( src, local, canonical ) VALUES( ?, ?, ? )'
                    execute( c, txt, data )

# --------------------------------------------------------------------------
#   Build title table from data in the Index.Json directory.

def build_titles( dc, c, conn ):
    print( "\nBuilding titles", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS titles;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS titles_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE titles (
                src VARCHAR(255),
                local VARCHAR(255),
                title_id MEDIUMINT(8) UNSIGNED,
                composer VARCHAR(255),
                lyricist VARCHAR(255),
                sheet VARCHAR(10),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id),
                UNIQUE( title_id, src, local )
                )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
        """
        execute( c, txt )

    if SQLITE:
        txt = """CREATE TABLE titles (
                src VARCHAR(255),
                local VARCHAR(255),
                title_id MEDIUMINT(8),
                composer VARCHAR(255),
                lyricist VARCHAR(255),
                sheet VARCHAR(10),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id),
                UNIQUE( title_id, src, local )
        )
        """
        execute( c, txt )

        if FULLTEXT and SQLITE:
            txt = """CREATE VIRTUAL TABLE titles_fts USING fts5(
                src,
                local,
                title_id,
                composer UNINDEXED,
                lyricist UNINDEXED,
                sheet UNINDEXED,
                content='titles',
                content_rowid='id'
            )
            """
            execute( c, txt )

    fb.traverse_sources( build_titles_from_one_index_source, c=c, dc=dc )

    if MYSQL:
        txt = "ALTER TABLE titles ADD INDEX( title_id ), ADD INDEX( local ), ADD INDEX( src )"

    if SQLITE:
        txt = "CREATE INDEX titles_index ON titles( title_id, local, src )"

    execute( c, txt )
    conn.commit()
    return 0

# --------------------------------------------------------------------------

def build_titles_from_one_index_source( src, **kwargs ):
    fb.get_music_index_data_by_src( src, proc_one_book, **kwargs )

# --------------------------------------------------------------------------

def proc_one_book( src, data, file, **kwargs ):
    c = kwargs[ 'c' ]
    dc = kwargs[ 'dc' ]
    local = data[ 'local' ]
    source = data[ 'source' ]
    contents = data[ 'contents' ]
    sheet_min = 999999
    sheet_max = 0
    # pages = []
    prior_sheet = -1
    prior_title = "prior-title"

    # print( f"   {local:50} {source:20} ({src})", file=sys.stderr, flush=True  )

    for content in contents:
        title = content[ 'title' ]
        title_id = fb.get_title_id_from_title( dc, title )

        sheet = content[ 'sheet' ] if not content[ 'sheet' ] == '-' else None

        composer = content[ 'composer' ] if 'composer' in content else None
        if composer:
            composer = composer.strip()

        lyricist = content[ 'lyricist' ] if 'lyricist' in content else None
        if lyricist:
            lyricist = lyricist.strip()

        proc_one_book_int( c, src, local, title_id, composer, lyricist, sheet )

        if sheet:
            sheet = sheet.strip()
            if not sheet.isnumeric():
                print( f"WARNING: Page number contains non-numerics: <{sheet}>, for {src}, {local}, {title}", file=sys.stderr, flush=True  )
                continue

            sheet_min = min( sheet_min, int(sheet) )
            sheet_max = max( sheet_max, int(sheet) )

        else:
            print( f"WARNING: Missing sheet number for {src}, {local}, prior sheet: {prior_sheet}, prior title: {prior_title}", file=sys.stderr, flush=True   )

        prior_sheet = sheet
        prior_title = title

    title_id = fb.get_title_id_from_title( dc, '_TitleFirst' )
    proc_one_book_int( c, src, local, title_id, None, None, str(sheet_min) )

    # page_mid = int( (page_min + page_max)/2)

    # title_id = fb.get_title_id_from_title( dc, '_Test-Title-Mid' )
    # proc_one_book_int( c, src, local, title_id, None, None, str(sheet_mid) )

    title_id = fb.get_title_id_from_title( dc, '_TitleLast' )
    proc_one_book_int( c, src, local, title_id, None, None, str(sheet_max) )

    # pages=sorted( pages )
    # print( f"src: {src}, local: {local}" )
    # print( pages )
    # print()

# ----------------------------------------------------------------------------------
#   Buffalo contains some duplicate data, same title, different call number I think. 
#       INSERT IGNORE to resolve that.

def proc_one_book_int( c, src, local, title_id, composer, lyricist, sheet ):

        data = ( src, local, title_id, composer, lyricist, sheet )

        if MYSQL:
            txt = 'INSERT IGNORE INTO titles ( src, local, title_id, composer, lyricist, sheet ) VALUES( %s, %s, %s, %s, %s, %s )'

        if SQLITE:
            txt = 'INSERT OR IGNORE INTO titles ( src, local, title_id, composer, lyricist, sheet ) VALUES( ?, ?, ?, ?, ?, ? )'

        execute( c, txt, data )

        if FULLTEXT and SQLITE:
            txt = 'INSERT OR IGNORE INTO titles_fts ( src, local, title_id, composer, lyricist, sheet ) VALUES( ?, ?, ?, ?, ?, ? )'
            execute( c, txt, data )

# ----------------------------------------------------------------------------------
#   Build titles_distinct table from data in the Index.Json directory.
#   This is first pass over Index.Json directory. Need titles_distinct to build titles.
#   Redo this using set() instead of intermediate int_titles for SQLITE case.
#       SELECT DISTINCT in Sqlite considers all columns distinct, Mysql only the specified column.
#       No! Doing it the same way for both, working from titles_distinct

def build_titles_distinct( c, conn ):
    print( "\nBuilding titles_distinct", file=sys.stderr, flush=True  )

    titles_distinct = set()
    raw_index = []

    fb.traverse_sources( build_titles_distinct_from_one_index_source, c=c, titles_distinct = titles_distinct, raw_index = raw_index )     # Builds titles_distinct set()

    txt = 'DROP TABLE IF EXISTS raw_index;'
    execute( c, txt )

    txt = 'DROP TABLE IF EXISTS titles_distinct;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS titles_distinct_fts;'
        execute( c, txt )

        txt = 'DROP TABLE IF EXISTS raw_index_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE titles_distinct (
            title VARCHAR(255),
            title_id MEDIUMINT UNSIGNED,
            PRIMARY KEY(title_id) )
            ENGINE = MYISAM
            CHARACTER SET 'utf8mb4'
        """
        execute( c, txt )

        txt = """CREATE TABLE raw_index(
            title_id MEDIUMINT UNSIGNED,
            src VARCHAR(255),
            local VARCHAR(255),
            file VARCHAR(255),
            line VARCHAR(255),
            id MEDIUMINT AUTO_INCREMENT,
            PRIMARY KEY(id) )
            ENGINE = MYISAM
            CHARACTER SET 'utf8mb4'
        """
        execute( c, txt )

    if SQLITE:
        txt = """CREATE TABLE titles_distinct (
                title VARCHAR(255),
                title_id INTEGER PRIMARY KEY              
                )
        """
        execute( c, txt )

        txt = """CREATE TABLE raw_index (
                src VARCHAR(255),
                local VARCHAR(255),
                file VARCHAR(255),
                line VARCHAR(255),
                title_id INTEGER,
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id)
                )
        """
        execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE titles_distinct_fts USING fts5(
            title,
            title_id,
            content='titles_distinct',
            content_rowid='title_id'
        )
        """
        execute( c, txt )

        txt = """CREATE VIRTUAL TABLE raw_index_fts USING fts5(
            title_id,
            local,
            src,
            file,
            content='raw_index',
            content_rowid='id'
        )
        """
        execute( c, txt )


    # --------------------------------------------------------------
    #   Build titles_distinct table directly from titles_distinct set instead
    #       of from an intermediate table. Inserting title_id here, remove AUTO INCREMENT in CREATE.

    for title_id, title in enumerate( sorted( titles_distinct )):

        data = ( title, title_id )

        txt = 'INSERT INTO titles_distinct ( title, title_id ) VALUES( %s, %s )'
        txt = fix_query( txt )
        execute( c, txt, data )

        if FULLTEXT and SQLITE:
            txt = 'INSERT INTO titles_distinct_fts ( title, title_id ) VALUES( ?, ? )'
            execute( c, txt, data )

    # --------------------------------------------------------------
    #   Add index here as using titles_distinct in get_title_id_from_title(), which is used by
    #       build_titles() and build_title2youtube(). Cut run time in about half.
    #       add_indexes() adds FULLTEXT index.  Need ordinary index for get_title_id_from_title().
    #   PRIMARY KEY is automatically indexed, don't need to add another here.

    if MYSQL:
        txt = "ALTER TABLE titles_distinct ADD INDEX( title ), ADD INDEX( title_id )"
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX titles_distinct_index ON titles_distinct( title, title_id )"
        execute( c, txt )

    # --------------------------------------------------------------
    #   WRW 1 Apr 2022 - Build raw_index table after add indexes because of the inner SELECT

    for item in raw_index:

        data = ( item[ 'src' ], item[ 'local' ], item[ 'file' ], item[ 'line' ], item[ 'title' ]  )

        txt = 'INSERT INTO raw_index( src, local, file, line, title_id ) VALUES( %s, %s, %s, %s, (SELECT title_id from titles_distinct WHERE title = %s ) )'
        txt = fix_query( txt )

        execute( c, txt, data )

    # --------------------------------------------------------------

    if MYSQL:
        txt = "ALTER TABLE raw_index ADD INDEX( src ), ADD INDEX( title_id ), ADD INDEX( local )"
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX raw_index_index ON raw_index( src, local, title_id )"
        execute( c, txt )

    # --------------------------------------------------------------

    conn.commit()
    return 0

# --------------------------------------------------------------------------

def build_titles_distinct_from_one_index_source ( src, **kwargs ):
    fb.get_music_index_data_by_src( src, proc_one_book_for_titles_distinct, **kwargs )

# --------------------------------------------------------------------------
#   Add each title to titles_distinct set().
#   WRW 22 Feb 2022 - Was getting a lot of duplicates in titles_distinct.      
#       Sets do not contain duplicates. Looks like capitalization problem
#       but that should have been done at add() time. Problem with diacriticals.
#       Corrected in fb_title_corrections().
#       Only do corrections in fb_title_corrections() at add time.

def proc_one_book_for_titles_distinct ( src, data, file, **kwargs ):

    c = kwargs[ 'c' ]
    titles_distinct = kwargs[ 'titles_distinct' ]       # WRW 27 Mar 2022 - Now passing titles_distinct through kwargs[]
    raw_index = kwargs[ 'raw_index' ]                   # WRW 1 Apr 2022 - Add raw_index
    contents = data[ 'contents' ]
    local = data[ 'local' ]                             # WRW 5 Apr 2022 - Need this, too.

    for line, content in enumerate( contents ):
        title = content[ 'title' ]                                               
        if title:
            titles_distinct.add( title )
        else:
            print( f"WARNING: falsey title on line {line+1} of {file}", file=sys.stderr, flush=True  )

        if 'file' in content:
            file = content[ 'file' ]
        else:
            print( f"WARNING: 'file' not found on line {line+1} of {file}", file=sys.stderr, flush=True  )

        if 'line' in content:
            line = content[ 'line' ]
        else:
            print( f"WARNING: 'line' not found on line {line+1} of {file}", file=sys.stderr, flush=True  )

        raw_index.append( {'title' : title, 'src' : src, 'local' : local, 'file' : file, 'line' : line } )

    titles_distinct.add( "_TitleFirst"  )
    titles_distinct.add( "_TitleLast"  )

# ----------------------------------------------------------------------------------

def build_title2youtube( dc, c, conn, show_found, show_not_found ):
    print( "\nBuilding titles2youtube", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS title2youtube;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS title2youtube_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE title2youtube(
                title_id MEDIUMINT(8) UNSIGNED,
                ytitle VARCHAR(255),
                duration VARCHAR(255),
                yt_id VARCHAR(255),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """
    if SQLITE:
        txt = """CREATE TABLE title2youtube(
                title_id MEDIUMINT(8),
                ytitle VARCHAR(255),
                duration VARCHAR(255),
                yt_id VARCHAR(255),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE title2youtube_fts USING fts5(
            title,
            ytitle UNINDEXED,
            title_id UNINDEXED,
            duration UNINDEXED,
            yt_id UNINDEXED,
            content='title2youtube',
            content_rowid='id'
        )
        """
        execute( c, txt )

    count_titles_total = count_titles_found = count_titles_not_found = 0

    with gzip.open( conf.val( 'youtube_index'), 'rt') as ifd:
        data = json.load( ifd )

        for content in data[ 'contents' ]:
            count_titles_total += 1
            title = content[ 'title' ]
            links = content[ 'links' ]

            title_id = fb.get_title_id_from_title( dc, title )

            if title_id:
                if show_found:
                    print( title, file=sys.stderr, flush=True  )
                count_titles_found += 1
                for link in links:
                    ytitle = link[ 'ytitle' ]
                    duration = link[ 'duration' ]

                    # url: https://www.youtube.com/watch?v=DMo6Ju8SJ8o
                    # url = link[ 'url' ]
                    # yt_id = re.sub( 'https://www\.youtube\.com/watch\?v=', '', url )

                    yt_id = link[ 'id' ]
                    data = ( title_id, ytitle, duration, yt_id )

                    txt = 'INSERT INTO title2youtube ( title_id, ytitle, duration, yt_id ) VALUES( %s, %s, %s, %s )'
                    txt = fix_query( txt )
                    execute( c, txt, data )

                    if FULLTEXT and SQLITE:
                        txt = 'INSERT INTO title2youtube_fts ( title_id, ytitle, duration, yt_id ) VALUES( ?, ?, ?, ? )'
                        execute( c, txt, data )

            else:
                count_titles_not_found += 1
                if show_not_found:
                    print( title, file=sys.stderr, flush=True  )

    # ----------------------

    if MYSQL:
        txt = "ALTER TABLE title2youtube ADD INDEX( title_id ), ADD INDEX( ytitle ), ADD FULLTEXT( ytitle )"
        execute( c, txt )

    if SQLITE:
        txt = "CREATE INDEX title2youtube_index ON title2youtube ( title_id, ytitle )"
        execute( c, txt )

    # ----------------------

    print( 
    f"""   Titles processed from {conf.val( 'youtube_index')}: {count_titles_total}
    Found in titles_distinct: {count_titles_found}
    Not found in titles_distinct: {count_titles_not_found}""",
    file=sys.stderr, flush=True  )

    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   Format: local book name | (starting page, offset)
#   WRW 5 Apr 2022 - get_page_from_sheet() was not working using sqlite. Looks
#       like problem is trying to use primary key 'id'. Add separate counter 'offset_id'.

def build_sheet_offsets( c, conn ):
    print( "\nBuilding sheet_offsets", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS sheet_offsets;'
    execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE sheet_offsets(
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                src VARCHAR(255),
                local VARCHAR(255),
                sheet_start SMALLINT,
                sheet_offset SMALLINT,
                offset_id MEDIUMINT UNSIGNED,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """
    if SQLITE:
        txt = """CREATE TABLE sheet_offsets(
                id MEDIUMINT AUTO_INCREMENT,
                src VARCHAR(255),
                local VARCHAR(255),
                sheet_start SMALLINT,
                sheet_offset SMALLINT,
                offset_id MEDIUMINT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    fb.traverse_sources( int_build_sheet_offsets, c=c )

    if MYSQL:
        txt = "ALTER TABLE sheet_offsets ADD INDEX( src ), ADD INDEX( local ), ADD INDEX( sheet_start)"
    if SQLITE:
        txt = "CREATE INDEX sheet_offsets_index ON sheet_offsets( src, local, sheet_start )"

    execute( c, txt )

    conn.commit()
    return 0

# --------------------------------------------------------------------------
#  select *, page + sheet_offset as corrected
#    from titles
#    join sheet_offsets using(local, src)
#    where page >= sheet_start limit 10;

def int_build_sheet_offsets( src, **kwargs ):
    c = kwargs[ 'c' ]

    print( f"   {src} {fb.get_source_from_src( src )}", file=sys.stderr, flush=True  )
    source = fb.get_source_from_src( src )

    # WRW 5 Mar 2022 - Removed sheetoffsets from config file.
    #   in lieu of hard-wired file name.

    # ifile = conf.val( 'sheetoffsets', source )    
    
    ifile = Path( conf.get_source_path( source ), conf.val( 'sheetoffsets', source ))
    with open( ifile ) as fd: 
        offset_id = 0
        for line in fb_utils.continuation_lines(fd):
            line = line.strip()
            if line.startswith( '#' ):
                continue
            if not len(line):
                continue
            local, offsets = line.split( '|' )
            local = local.strip()
            offsets = offsets.strip()

            for mo in re.finditer( '\((.*?),(.*?)\)', offsets ):
                sheet_start = int( mo.group(1).strip() )
                sheet_offset = int( mo.group(2).strip() )

                data = ( src, local, sheet_start, sheet_offset, offset_id )
                txt = 'INSERT INTO sheet_offsets ( src, local, sheet_start, sheet_offset, offset_id ) VALUES( %s, %s, %s, %s, %s )'
                txt = fix_query( txt )
                execute( c, txt, data )
                offset_id += 1

# --------------------------------------------------------------------------
#   os.walk( folder ) returns generator that returns list of folders and list of files
#       in 'folder'.

def old_listfiles( folder ):
    for root, folders, files in os.walk(folder):
        for file in files:
            yield (root, file)
            # yield os.path.join(root, file)

# -----------------------------------------------------------------------

def build_music_files( c, conn ):
    print( "\nBuilding music_files", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS music_files;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS music_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE music_files(
                rpath VARCHAR(255),
                file VARCHAR(255),
                fb_flag CHAR(1),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """
    if SQLITE:
        txt = """CREATE TABLE music_files(
                rpath VARCHAR(255),
                file VARCHAR(255),
                fb_flag VARCHAR(1),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE music_files_fts USING fts5(
            rpath,
            file,
            fb_flag,
            content='music_files',
            content_rowid='id'
        )
        """
        execute( c, txt )

    file_count = 0
    file_count_by_ext = {}

    # ------------------------------------------------------------------------
    #   WRW 2 Mar 2022 - Recode this using Path() and add fakebook_folder flag.
    #       A bit cleaner and understandable. Added fb_flag to limit files for canon2file editing.

    music_folders = [ x for x in conf.v.music_file_folders.split('\n') ]
    fakebook_folders = [ x for x in conf.v.c2f_editable_music_folders.split('\n') ]       # Starting point for canon2file editing.

    root = Path( conf.v.music_file_root ).expanduser()
    for folder in music_folders:

        if folder in fakebook_folders:
            fb_flag = 'y'
        else:
            fb_flag = 'n'

        for file in Path( root, folder ).glob( '**/*.[pP][dD][fF]' ):
            rpath = file.relative_to( root ).parent.as_posix()
            data = (rpath, file.name, fb_flag )
            txt = 'INSERT INTO music_files ( rpath, file, fb_flag ) VALUES( %s, %s, %s )'
            txt = fix_query( txt )
            execute( c, txt, data )

            if FULLTEXT and SQLITE:
                txt = 'INSERT INTO music_files_fts ( rpath, file, fb_flag ) VALUES( ?, ?, ? )'
                execute( c, txt, data )

            file_count += 1
            file_count_by_ext[ file.suffix ] = file_count_by_ext.setdefault( file.suffix, 0 ) + 1

    # ----------------------

    if MYSQL:
        txt = "ALTER TABLE music_files ADD FULLTEXT( rpath ), ADD FULLTEXT( file )"
        execute( c, txt )

    # ----------------------

    print( f"   Music files total: {file_count}", file=sys.stderr, flush=True  )
    # for ext in file_count_by_ext:
    #     print( f"      {ext}: {file_count_by_ext[ ext ]}", file=sys.stderr, flush=True  )

    conn.commit()
    return 0

# --------------------------------------------------------------------------

def build_midi_files( c, conn ):
    print( "\nBuilding midi_files", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS midi_files;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS midi_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE midi_files(
                rpath VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """

    if SQLITE:
        txt = """CREATE TABLE midi_files(
                rpath VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE midi_files_fts USING fts5(
            rpath,
            file,
            content='midi_files',
            content_rowid='id'
        )
        """
        execute( c, txt )

    file_count = 0

    for folder in fb.Midi_Folders:
        path = Path( fb.Midi_File_Root, folder ).as_posix()

        print( f"   {folder}", file=sys.stderr, flush=True  )
        # print( f"  Midi_File_Root: {fb.Midi_File_Root},    path: {path}" )

        for root, file in fb.listfiles( path ):         # fb.listfiles() is doing os.walk()
            # _, ext = os.path.splitext( file )
            ext = Path( file ).suffix

            rpath = Path( root ).relative_to( Path( fb.Midi_File_Root ) ).as_posix()

            # print( f"    Root: {root}\n    Rel_path: {rel_path}\n    File: {file}" )

            if ext == '.mid' or ext == '.MID':
                # print( f"    rpath: {rpath}\n    File: {file}" )

                data = (rpath, file)
                txt = 'INSERT INTO midi_files ( rpath, file ) VALUES( %s, %s )'
                txt = fix_query( txt )
                execute( c, txt, data )

                if FULLTEXT and SQLITE:
                    txt = 'INSERT INTO midi_files_fts ( rpath, file ) VALUES( ?, ? )'
                    execute( c, txt, data )

                file_count += 1

            # ---------------------------------------------------------

    print( f"   Midi files total: {file_count}", file=sys.stderr, flush=True  )

    if MYSQL:
        txt = "ALTER TABLE midi_files ADD FULLTEXT( rpath ), ADD FULLTEXT( file )"
        execute( c, txt )

    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   WRW 27 Apr 2022 - Dinking around with chordpro and jjazz lab files

def build_chordpro_files( c, conn ):
    print( "\nBuilding chordpro_files", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS chordpro_files;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS chordpro_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE chordpro_files(
                title VARCHAR(255),
                artist VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """

    if SQLITE:
        txt = """CREATE TABLE chordpro_files(
                title VARCHAR(255),
                artist VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE chordpro_files_fts USING fts5(
            title,
            artist,
            file,
            content='chordpro_files',
            content_rowid='id'
        )
        """
        execute( c, txt )

    file_count = 0

    for folder in conf.val( 'chordpro_folders' ):
        path = Path( conf.val( 'chordpro_file_root' ), folder ).as_posix()

        print( f"   {folder}", file=sys.stderr, flush=True  )

        for root, file in fb.listfiles( path ):         # fb.listfiles() is doing os.walk()
            ext = Path( file ).suffix

            rpath = Path( root ).relative_to( Path( conf.val( 'chordpro_file_root' )) ).as_posix()

            # print( f"    Root: {root}\n    Rel_path: {rpath}\n    File: {file}" )

            if ext == '.chopro' or ext == '.cho' or ext == 'crd':
                # print( f"    rpath: {rpath}\n    File: {file}" )

                rfile = Path( rpath, file ).as_posix()

                #   /// RESUME - extracting artist from file, OK in the one archive I downloaded.

                artist = Path( root ).name
                parts = re.findall(r'[A-Z][a-z0-9]+|[A-Z]', artist)         # Splits on case boundaries
                artist = ' '.join( parts )

                title = Path( file ).stem               # Make title from file name
                parts = re.findall(r'[A-Z][a-z0-9]+|[A-Z]', title)         # Splits on case boundaries
                title = ' '.join( parts )

                if title or artist:                           # Some zero len
                    data = (title, artist, rfile)
                    txt = 'INSERT INTO chordpro_files ( title, artist, file ) VALUES( %s, %s, %s )'
                    txt = fix_query( txt )
                    execute( c, txt, data )

                    if FULLTEXT and SQLITE:
                        txt = 'INSERT INTO chordpro_files_fts ( title, artist, file ) VALUES( ?, ?, ? )'
                        execute( c, txt, data )

                    file_count += 1

            # ---------------------------------------------------------

    print( f"   Chordpro files total: {file_count}", file=sys.stderr, flush=True  )

    if MYSQL:
        txt = "ALTER TABLE chordpro_files ADD FULLTEXT( title ), ADD FULLTEXT( file )"
        execute( c, txt )

    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   WRW 27 Apr 2022 - Dinking around with chordpro and jjazz lab files

def build_jjazz_files( c, conn ):
    print( "\nBuilding jjazz_files", file=sys.stderr, flush=True  )

    txt = 'DROP TABLE IF EXISTS jjazz_files;'
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = 'DROP TABLE IF EXISTS jjazz_files_fts;'
        execute( c, txt )

    if MYSQL:
        txt = """CREATE TABLE jjazz_files(
                title VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT UNSIGNED AUTO_INCREMENT,
                PRIMARY KEY(id) )
                ENGINE = MYISAM
                CHARACTER SET 'utf8mb4'
            """

    if SQLITE:
        txt = """CREATE TABLE jjazz_files(
                title VARCHAR(255),
                file VARCHAR(255),
                id MEDIUMINT AUTO_INCREMENT,
                PRIMARY KEY(id) )
            """
    execute( c, txt )

    if FULLTEXT and SQLITE:
        txt = """CREATE VIRTUAL TABLE jjazz_files_fts USING fts5(
            title,
            file,
            content='jjazz_files',
            content_rowid='id'
        )
        """
        execute( c, txt )

    file_count = 0

    for folder in conf.val( 'jjazz_folders' ):
        path = Path( conf.val( 'jjazz_file_root' ), folder ).as_posix()

        print( f"   {folder}", file=sys.stderr, flush=True  )

        for root, file in fb.listfiles( path ):         # fb.listfiles() is doing os.walk()
            ext = Path( file ).suffix

            rpath = Path( root ).relative_to( Path( conf.val( 'jjazz_file_root' )) ).as_posix()

            # print( f"    Root: {root}\n    Rel_path: {rpath}\n    File: {file}" )

            if ext == '.sng':
                # print( f"    rpath: {rpath}\n    File: {file}" )

                rfile = Path( rpath, file ).as_posix()

                # Make title from file name

                title = Path( file ).stem
                parts = re.findall(r'[A-Z][a-z0-9]+|[A-Z]', title)         # Splits on case boundaries
                title = ' '.join( parts )

                if title:                               # Some zero len
                    data = (title, rfile)
                    txt = 'INSERT INTO jjazz_files ( title, file ) VALUES( %s, %s )'
                    txt = fix_query( txt )
                    execute( c, txt, data )

                    if FULLTEXT and SQLITE:
                        txt = 'INSERT INTO jjazz_files_fts ( title, file ) VALUES( ?, ? )'
                        execute( c, txt, data )

                    file_count += 1

            # ---------------------------------------------------------

    print( f"   JJazzLab files total: {file_count}", file=sys.stderr, flush=True  )

    if MYSQL:
        txt = "ALTER TABLE jjazz_files ADD FULLTEXT( title ), ADD FULLTEXT( file )"
        execute( c, txt )

    conn.commit()
    return 0

# --------------------------------------------------------------------------
#   WRW - 23 Feb 2022 - Convert the raw index data from multiple sources to
#       uniform style in json files in Music-Index. Originally done by Makefile.
#   
#   This includes built-in knowledge of directory structure since can't assume have
#   config file yet. Or can we? If so, this information is in that though I would prefer it not be.
#   This might be better way to do it as is driven only by the directory names in Index-Sources.
#   Note that must:
#           conf.set_cwd( f"{os.getcwd()}/../../bin" )
#       in each of the source-specific do_* files for getting config values
#       and so that the do* files cwd is the local directory.
#       Best way to do it? Yes. See 13 Mar 2022.
#   WRW 5 March 2022 - Change to use source names and 'command' from config file.
#   WRW 13 March 2022 - Set PYTHONPATH so source-specific do_*.py scripts can find the modules here.
#   Removed conf.set_cwd( f"{os.getcwd()}/../../bin" ) in do_*.py files.

def convert_raw_source():

    # if conf.Package_Type == 'PyInstaller' or conf.Package_Type == 'Nuitka':
    #     print( "WARNING: 'Process Index Sources' is not supported from a bundled installation.", file=sys.stderr() )
    #     print( "    Please reinstall with pip from a Setuptools distribution or with tar from a Tar distribution. ", file=sys.stderr() )
    #     return 1
    #     # sys.exit(1)

    os.environ[ 'PYTHONPATH' ] = Path( __file__ ).parent.resolve().as_posix()

    sources = conf.get_sources()
    for source in sources:
        folder = conf.val( 'folder', source )
        print( folder )

        src = conf.val( 'src', source )                                                             
        command = conf.val( 'command', source )
        path = Path( folder )

        if path.is_dir():
            print( f"Processing: {path.name}", flush=True )
            os.chdir( path )
            if( os.access( command, os.X_OK) ):
                full_command = [ command, '--src', src ]

                #   WRW 15 Mar 2022 - Replaced run with popen so can capture output when running as package.
                #   popen = subprocess.run( full_command, text=True )

                extcmd_popen = subprocess.Popen( full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True )
                for line in extcmd_popen.stdout:
                    print( line, end='', flush=True )

                extcmd_popen.stdout.close()
                rcode = extcmd_popen.wait()
                print( '' )

            else:
                print( f"ERROR-DEV: command {command} not found or not executable in convert_raw_source()" )
                return 1
                # sys.exit(1)

        else:
            print( f"ERROR-DEV: unexpected path {path} in convert_raw_source()" )
            return 1
            # sys.exit(1)

    return 0

# --------------------------------------------------------------------------
#   WRW 2 Apr 2022 - Found a lot of typos in the raw index. Make a table to harmonize them.
#       I tried comparing all titles to all titles. Not a good idea.
#       Try a small window around the current since most typos will sort nearby.
#       Inspect: cut -d' ' -f1 t | sort | uniq -c | sort -k 2 -r -n | more
#   This is purely experimental at present. Not sure if will use it. Results look
#       promising but there are several false positives. Minimum length is helping that.
#   Stopped work while trying to accumulate results. Incomplete.

def build_corrections_file( dc, conn ):

    titles = []
    window_size = 100       # 100 vs 10 costs little in time but picks up almost twice the typos.
    levenshtein_limit = 2   # 0 not included.
    size_minimum = 10       # Don't test words shorter than this

    similars = {}

    txt = """SELECT title FROM titles_distinct
             ORDER BY TITLE
          """

    execute( dc, txt )
    rows = dc.fetchall()
    if rows:
        for row in rows:                    # Build array of all titles
            titles.append( row[ 'title' ] )

        i = 0
        while i < len(titles)-window_size/2:
            title1 = titles[ i ]           
            if len(title1) >= size_minimum:
                for j in range( -1 * int(window_size/2), int(window_size/2) + 1):
                    if j == 0:
                        continue
                    title2 = titles[ i + j ]           
                    if len(title2) >= size_minimum:
                        d = Levenshtein.distance( title1, title2 )
                        if d <= levenshtein_limit:
                            # print( f"{d} <{title1}> <{title2}>" )
                            similars.setdefault( title1, [] ).append( title2 )
            i += 1

    # ------------------------------------------------
    #   Build data structures

    primaries = set()               # Primary is first one seen of similars
    alternates = {}

    for title in similars:
        if (not title in alternates) and (not title in primaries):
            primaries.add( title )
            for alt_title in similars[ title ]:
                alternates[ alt_title ] = title

        else:
            for alt_title in similars[ title ]:
                if not alt_title in alternates:
                    alternates[ alt_title ] = title

    # ------------------------------------------------
    #   Test structures against all titles

    for title in titles:
        # if title in primaries:
        #     print( f"Pri: <{title}>" )

        if title in alternates:
            print( f"{title} | {alternates[ title ]}" )

    # ------------------------------------------------

    return 0

# --------------------------------------------------------------------------
#   WRW 3 Apr 2022 - Testing only for addition of leading 'The'
#   Problem with 'Beyond The Blue Horizon | The Beyond The Blue Horizon'
#   Note: This reads from titles_distinct. Must run after titles_distinct
#       changes and then re-run --convert_raw.

def build_the_corrections_file( dc, conn ):

    titles = []
    titles_set = set()

    txt = """SELECT title FROM titles_distinct
             ORDER BY TITLE
          """
    execute( dc, txt )
    rows = dc.fetchall()

    ofile = Path( conf.val( 'corrections' )).with_suffix( '.B.txt' )                        
    with open( ofile, 'w' ) as ofd:

        if rows:
            for row in rows:                    # Build array of all titles
                titles.append( row[ 'title' ] )
                titles_set.add( row[ 'title' ] )

            for title in titles:
                ntitle = f"The {title}"
                if ntitle in titles_set:            # Does a title with 'The' prefix exist?
                    print( f"{title} | {ntitle}", file=ofd )  # Yes, translate one without to one with.

    return 0

# --------------------------------------------------------------------------
#   Build audio index json file from MySql audio_files table.
#   Used only during development to save the time of rescanning the audio files
#       when developing the Sqlite3 database. Not accessible from Birdland menu.

def do_extract_audio( conn ):
    conn.close()    # Close conn opened in do_main(), could be sqlite or mysql.
    conf.set_driver( True, False, False )           # Always use MYSQL here.
    conf.set_class_variables()                      # WRW 18 Mar 2022 - Have to repeat after set_driver()
    import MySQLdb
    conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
    dc = conn.cursor(MySQLdb.cursors.DictCursor)
    fb.set_dc( dc )
    do_extract_audio_data( dc )
    conn.commit()
    conn.close()
    sys.exit(0)         # Ok, special case, never used from birdland.py

# --------------------------------------------------------------------------
#   Move into function to keep c and dc local, not global, to be sure not depending on global.
#   Must pull create and index out of primary functions and into build_sheet_offsets()
#   Reminder, run build-tables.py again after download YouTube links.
#   First time to get titles_distinct used to drive getting YouTube links.
#   Second time to build title2youtube table.

@click.command( context_settings=dict(max_content_width=120) )
@click.option( "-c", "--confdir",               help="Use alternate config directory" )
@click.option( "-a", "--all", is_flag=True, help="Build tables marked with *, does not scan audio" )
@click.option( "-d", "--database",      help="Use database sqlite or mysql, default sqlite", default='sqlite' )

@click.option( "--convert_raw", is_flag=True, help="Convert raw index source files" )

@click.option( "--src_priority", is_flag=True, help="* Build src_priority table" )
@click.option( "--midi", is_flag=True, help="* Scan midi_files and build midi table" )
@click.option( "--chordpro", is_flag=True, help="* Scan ChordPro files and build chordpro table" )
@click.option( "--jjazz", is_flag=True, help="* Scan JJazzLab files and build jjazz table" )
@click.option( "--music_files", is_flag=True, help="* Build music_files" )
@click.option( "--offset", is_flag=True, help="* Build sheet offsets table" )
@click.option( "--canonical", is_flag=True, help="* Build canonicals table" )
@click.option( "--canon2file", is_flag=True, help="* Build canonical2file table" )
@click.option( "--local2canon", is_flag=True, help="* Build local2canonical table" )
@click.option( "--titles_distinct", is_flag=True, help="* Build titles_distinct" )
@click.option( "--titles", is_flag=True, help="* Build titles" )
@click.option( "--corrections", is_flag=True, help="* Build title corrections file" )
@click.option( "--audio_files", is_flag=True, help="* Build audio_files from json table." )
@click.option( "--the_corrections", is_flag=True, help="Build 'The' title corrections file" )
@click.option( "--title2youtube", is_flag=True, help="Build title2youtube table from data obtained by get-youtube-links.py" )

@click.option( "--scan_audio", is_flag=True, help="Build json table from audio file scan. *** Avoid, may take a long time." )

@click.option( "--page_count", is_flag=True, help="Build page_count table from canonical2file table" )
# @click.option( "--extract_audio", is_flag=True, help="Build json table from existing MySql Database (transition only)" )
@click.option( "--fail", is_flag=True, help="Return failure for testing" )

#  extract_audio,

def do_main( all, database, offset, canonical, midi, canon2file, local2canon, title2youtube,
             src_priority, music_files, titles_distinct, titles,
             scan_audio, audio_files, confdir, convert_raw, corrections, the_corrections, fail,
             jjazz, chordpro, page_count
            ):

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
        return 1
        # sys.exit(1)

    # ---------------------------------------------------------------

    fb = fb_utils.FB()
    fb.set_driver( MYSQL, SQLITE, False )
    conf = fb_config.Config()
    conf.set_driver( MYSQL, SQLITE, False )

    os.chdir( os.path.dirname(os.path.realpath(__file__)))      # Run in directory where this lives.

    # conf.set_install_cwd( os.getcwd() )

    # ---------------------------------------------------------------
    #   WRW 7 Mar 2022 - More robust startup checking.
    #       Don't even run build-tables.py until have at least basic configuration set up.

    results, success = conf.check_home_config( confdir )
    if not success:
        print( f"ERROR: Error in home configuration:", file=sys.stderr )
        print( '\n'.join( results ))
        return 1
        # sys.exit(1)

    results, success = conf.check_specified_config( confdir )
    if not success:
        print( f"ERROR: Error in specified configuration:", file=sys.stderr )
        print( '\n'.join( results ))
        return 1
        # sys.exit(1)

    conf.get_config( confdir )
    conf.set_class_variables()      # WRW 6 Mar 2022 - Now have to do this explicitly
    fb.set_classes( conf )
    fb.set_class_config()

    results, success = conf.check_hostname_config()
    if not success:
        print( f"ERROR: Error in host-specific configuration:", file=sys.stderr )
        print( '\n'.join( results ))
        return 1
        # sys.exit(1)

    # ---------------------------------------------------------------
    #   WRW 7 Mar 2022 - Another check for pathological cases. By now
    #       all should be set up but this may help in unusual testing cases.

    results, success = conf.check_confdir_content()
    if not success:
        print( f"ERROR: Error in configuration directory content:", file=sys.stderr )
        print( '\n'.join( results ))
        return 1
        # sys.exit(1)

    # ---------------------------------------------------------------
    #   WRW 24 Feb 2022 - Must have user and password already set up
    #       in configuration to proceed here with MySql.

    if MYSQL:
        results, success = conf.check_database( database )
        if not success:
            print( f"ERROR: Error in database configuration (build_tables.py):", file=sys.stderr )
            print( '\n'.join( results ))
            return 1
            # sys.exit(1)

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
        return 1
        # sys.exit(1)

    # ---------------------------------------------------------------
    #   WRW 22 Mar 2022 - Add rcode so can see it in calling program.

    rcode = 0

    # ---------------------------------
    #   Run all the Index-Source/do_*.py files      # Do before all, titles_distinct and titles so can do in one call.

    if convert_raw:
        rcode += convert_raw_source()

    # ---------------------------------

    if all:
        rcode += build_source_priority( c, conn )
        rcode += build_midi_files( c, conn )                                                                    
        rcode += build_chordpro_files( c, conn )
        rcode += build_jjazz_files( c, conn )
        rcode += build_music_files( c, conn )
        rcode += build_sheet_offsets( c, conn )
        rcode += build_local2canonical( c, conn )
        rcode += build_canonicals( c, conn )
        rcode += build_canonical2file( c, conn )
        rcode += build_page_count( dc, c, conn )
        rcode += build_titles_distinct( c, conn )
        rcode += build_titles( dc, c, conn )                     # After build_titles_distinct()
        rcode += build_title2youtube( dc, c, conn, False, False )       # dc, Ifile, show_found, show_not_found
        rcode += build_audio_files( c )

    # ---------------------------------

    if scan_audio:                          # This takes a long time. Use sparingly. Keep separate from --all.
        rcode += do_scan_audio_files()      # Keep above build_audio_files() so can do both in one invocation.

    # ---------------------------------

    if audio_files:
        rcode += build_audio_files( c )

    if music_files:
        rcode += build_music_files( c, conn )

    if src_priority:
        rcode += build_source_priority( c, conn )

    if offset:
        rcode += build_sheet_offsets( c, conn )         # Does its own create and indexes.

    if midi:
        rcode += build_midi_files( c, conn )         # Does its own create and indexes.

    if chordpro:
        rcode += build_chordpro_files( c, conn )      # Does its own create and indexes.

    if jjazz:
        rcode += build_jjazz_files( c, conn )         # Does its own create and indexes.

    if canonical:
        rcode += build_canonicals( c, conn )

    if canon2file:
        rcode += build_canonical2file( c, conn )

    if local2canon:
        rcode += build_local2canonical( c, conn )

    if titles_distinct:
        rcode += build_titles_distinct( c, conn )

    if corrections:
        rcode += build_corrections_file( dc, conn )

    if the_corrections:
        rcode += build_the_corrections_file( dc, conn )

    if titles:
        rcode += build_titles( dc, c, conn )

    if page_count:
        rcode += build_page_count( dc, c, conn )

    if title2youtube:
        rcode += build_title2youtube( dc, c, conn, False, False )       # dc, Ifile, show_found, show_not_found

    # ---------------------------------
    #   This always reads from MySql DB. Needed during transition from MySql to Sqlite to extract audio_files
    #       from MySql into Sqlite DB to save time of scanning audio files. Always follow with build_audio_files().

    # if extract_audio:               # Only used during development, ok to exit to avoid commit() and close() on closed DB.
    #     do_extract_audio( conn )    # Calls sys.exit(), never returns.

    # ---------------------------------

    if fail:
        return 1

    # ---------------------------------

    conn.commit()
    conn.close()

    # ---------------------------------

    return rcode

# --------------------------------------------------------------------------
#   WRW 22 Mar 2022 - Include 'standalone_mode=False' in call to do_main() to prevent
#       click() from exiting at completion. We don't want it to exit when calling this
#       from birdland.py as a module.
#   Only use standalone_mode = False when calling as module. Undesirable because it
#       interferes with error messages. We have control of args when calling from birdland.
#   WRW 23 Mar 2022 - Save and restore 'dc'. We are setting dc with value created here but
#       then closing it. fb_utils() then was using closed value.
#   WRW 17 May 2022 - Perhaps don't even bother with setting fb.set_dc(), let fb_utils.py use
#       the dc set in birdland.py?

def aux_main( args ):      # Called as module from birdland.                           
    global Old_Dc
    save_sys_argv = sys.argv
    sys.argv = [ x for x in args ]
    rcode = do_main( standalone_mode=False )
    if Old_Dc:
        fb.set_dc( Old_Dc )
        Old_Dc = None

    sys.argv = save_sys_argv
    return rcode

def main():
    do_main()

if __name__ == '__main__':
    do_main()

# --------------------------------------------------------------------------

