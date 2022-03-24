#!/usr/bin/python
# ---------------------------------------------------------------------------------------
#   birdland.py

#   Originally GUI Interface to the Bluebird database. Search database for title and
#   show tables of titles in music files, audio files, and links to YouTube.

#   WRW 6 Oct 2020 - Converted from db-play.py to use pure Qt with UI from QtDesigner.
#       db-play.py was an interface to just local audio files.

#   WRW 15 Dec 2021 - Don't see where did any qt work except to make the gui .ui file.
#       Switched back to system-wide installation of pysimplegui and an updated version of it.

#   WRW Dec 2021 - Used the above as a starting point and expanded it to pretty much
#       all of Birdland from years ago.
#       This is a PySimpleGUI implementation of the function of Birdland, which I worked on
#       ten to eleven years ago.

#   WRW 4 Feb 2022 - Changed name to birdland.py and database to Birdland. Lots of bluebird references
#       will inevitably linger here.

#   WRW 22 Feb 2022 - During startup (no database) I saw a situation where all files in Music Index showed
#       none independent of the show missing file option.

# ---------------------------------------------------------------------------------------

import PySimpleGUI as sg
import tkinter as tk

# import PySimpleGUIQt as sg        # A long way from working.
import os
import sys
import platform
import signal
import subprocess
import MySQLdb
import socket
import click
import fitz
from pathlib import Path
from collections import defaultdict
import sqlite3
import re
import configobj                 
import json
import time
import copy
import datetime
import importlib.metadata        

# import beepy

import fb_utils
import fb_pdf
import fb_metadata
import fb_setlist
import fb_layout
import fb_index_mgmt
import fb_index_diff
import fb_local2canon_mgmt
import fb_canon2file_mgmt
import fb_config
import fb_make_desktop

# =======================================================================================
#   A few Constants

# BirdlandVersion = "0.1 Beta"

folder_icon =       'Icons/icons8-file-folder-16.png'
music_file_icon =   'Icons/Apps-Pdf-icon.png'
audio_file_icon =   'Icons/audio-x-generic-icon.png'
BL_Icon = fb_utils.BL_Icon

extcmd_popen = None

# ---------------------------------------------------------------------------------------
#   A few globals.

music_tree = None
music_tree_aux = {}     # Metadata for music_tree

audio_tree = None
audio_tree_aux = {}     # Metadata for audio_tree

# ----------------------------------------
#   WRW 5 Mar 2022 - I want to localize status info in a class and add
#       a couple of indicators of audio and midi of title available.

class Status():
    def __init__( self, bar ):
        self.bar = bar
        self.pdf_count = 0
        self.pdf_len = 0
        self.audio_count = 0
        self.audio_len = 0
        self.music_count = 0
        self.music_len = 0
        self.midi_count = 0
        self.midi_len = 0
        self.youtube_count = 0
        self.youtube_len = 0
        self.current_audio = False
        self.current_midi = False

    def set_music_index( self, count, len ):
        self.pdf_count = count
        self.pdf_len = len

    def set_audio_index( self, count, len ):
        self.audio_count = count
        self.audio_len = len

    def set_music_files( self, count, len ):
        self.music_count = count
        self.music_len = len

    def set_midi_files( self, count, len ):
        self.midi_count = count
        self.midi_len = len

    def set_youtube_index( self, count, len ):
        self.youtube_count = count
        self.youtube_len = len

    def set_current_audio( self, val ):
        self.current_audio = val

    def set_current_midi( self, val ):
        self.current_midi = val

    def show( self ):
        # audio_avail = 'Audio' if self.current_audio else ''
        # midi_avail =  'Midi'  if self.current_midi else  ''
        audio_avail = '\U0001F50a' if self.current_audio else ''
        midi_avail =  '\U0001f39d '  if self.current_midi else  ''

        results =  f"Search Results:   "
        results += f"Music Index: {self.pdf_len:>4} of {self.pdf_count:>4}      "
        results += f"Audio Index: {self.audio_len:>4} of {self.audio_count:>4}      "
        results += f"Music Files: {self.music_len:>4} of {self.music_count:>4}      "
        results += f"Midi Files: {self.midi_len:>4} of {self.midi_count:>4}      "
        results += f"YouTube Index: {self.youtube_len:>4} of {self.youtube_count:>4}      "
        results += f"{audio_avail:>10}    {midi_avail:>10}"
    
        self.bar.update( results )

# ----------------------------------------
#   WRW 7 Mar 2022 - Add a record/playback facility for testing
#   It sort of works:
#       User input is not reflected in GUI text boxes, tabs, selections, etc.
#       It breaks when get down to tkinter or thereabouts.

class Record():
    def __init__(self, file ):
        self.record_journal = []
        self.event_start_time = time.time()
        self.file = file
        self.journal_index = 0

    def rec( self, event, values ):
        self.record_journal.append( [event, copy.deepcopy( values ), time.time() - self.event_start_time ] )
        event_start_time = time.time()

    def save( self ):
        with open( self.file, 'wt' ) as ofd:
            json.dump( self.record_journal, ofd, indent=4 )

    def load( self ):
        with open( self.file ) as ifd:
            self.record_journal = json.load( ifd )
            self.journal_index = 0

    def get( self ):
        event, values, last_sleep = self.record_journal[ self.journal_index ]
      # values = copy.deepcopy( values )
        self.journal_index += 1
        return event, values, last_sleep

# ----------------------------------------
#   Extract a few paramaters from configuration and set in globals.
#   Must appear before call to it below.
#   /// RESUME - later rmove globals completely and ref conf.v.xxx directly.
#       NO! Use conf.val( 'option-id' )

def set_local_config():

    global Select_Limit, Source_Priority
    global UseExternalMusicViewer 
    global ShowIndexMgmgTabs 
    global ShowCanon2FileTab
    global DatabaseUser, DatabasePassword

    UseExternalMusicViewer  = conf.val( 'use_external_music_viewer' )
    Select_Limit            = conf.val( 'select_limit' )
    Source_Priority         = conf.val( 'source_priority' )
    ShowIndexMgmgTabs       = conf.val( 'show_index_mgmt_tabs' )
    ShowCanon2FileTab       = conf.val( 'show_canon2file_tab' )

    #   No longer needed with move to sqlite. /// RESMUME make connitional?

    # DatabaseUser            = conf.val( 'database_user' )
    # DatabasePassword        = conf.val( 'database_password' )

# --------------------------------------------------------------------------
#   Initialize classes in external modules.
#   RESUME - Look into inheritance for this.

conf =  fb_config.Config()
fb =    fb_utils.FB()
pdf =   fb_pdf.PDF()
meta =  fb_metadata.Meta()
toc =   fb_metadata.TableOfContents()
sl =    fb_setlist.Setlist()
mgmt =  fb_index_mgmt.Mgmt()
diff =  fb_index_diff.Diff()
l2c  =  fb_local2canon_mgmt.L2C()
c2f  =  fb_canon2file_mgmt.C2F()

# fb.set_driver( MYSQL, SQLITE )
# meta.set_driver( MYSQL, SQLITE )

# =======================================================================================
#   Replace %s with ? if using SQLITE

def fix_query( query ):
    if SQLITE:
        query = query.replace( '%s', '?' )
    return query

# ---------------------------------------------------------------------------

def set_index_mgmt_visibility( v ):
    global ShowIndexMgmgTabs 
    ShowIndexMgmgTabs = v

    window[ 'tab-index-mgmt' ].update( visible = v )
    window[ 'tab-index-diff' ].update( visible = v )
    window[ 'tab-local2canon-mgmt' ].update( visible = v )

# -------------------------------------

def set_canon2file_visibility( v ):
    global ShowCanon2FileTab
    ShowCanon2FileTab = v

    window[ 'tab-canon2file-mgmt' ].update( visible = v )

# -------------------------------------

def toggle_index_mgmt_visibility():
    if( ShowIndexMgmgTabs ):
        set_index_mgmt_visibility( False )
    else:
        set_index_mgmt_visibility( True )

def toggle_canon2file_visibility():
    if( ShowCanon2FileTab ):
        set_canon2file_visibility( False )
    else:
        set_canon2file_visibility( True )

# --------------------------------------------------------------
#   Call after run conf.do_configure()
#   Immediately update parameters with changed config.
#   Do this only when birdland fully launches, not on initial configuration window.

def do_configure_save_update():

    fb.set_class_config( )
    pdf.set_class_config( )
    sl.set_class_config( )
    mgmt.set_class_config( )
    l2c.set_class_config( )
    c2f.set_class_config( )
    set_local_config( )

    set_index_mgmt_visibility( ShowIndexMgmgTabs )
    set_canon2file_visibility( ShowCanon2FileTab )

    #   Not sure if want to hide entire PDF Viewer tab. Some metadata there might
    #       be useful even with external viewer. Yes, Definitely keep it.

    if conf.val( 'use_external_music_viewer' ):
        window['display-control-buttons' ].update( visible = False )
        window['display-control-buttons' ].hide_row()
    else:
        window['display-control-buttons' ].unhide_row()
        window['display-control-buttons' ].update( visible = True )

    #   This doesn't change theme dynamically. Should it? No. Well documented in discussion that it does not.
    #   sg.theme( conf.val( 'theme' ) )

# --------------------------------------------------------------
#   Find the last key + 1 in aux

def new_key( aux ):
    if aux.keys():
        return max( aux.keys() ) + 1
    else:
        return 1

# ------------------------------------------------

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))

# ------------------------------------------------
#        tree.insert(parent,
#                    key,
#                    text,
#                    values,
#                    icon = None)

def initialize_browse_tree( tree_key, tree, aux, valid_folders, root_path ):

    items = sorted( os.listdir( root_path ) )   # Items are relative to root, i.e. dirname
    for item in items:
        if os.path.isdir( os.path.join( root_path, item )):
            if item in valid_folders:
                key = new_key( aux )

                aux[ key ] = { 'kind'     : 'dir',
                               'relpath'  : item,
                               'file'     : '',
                               'children' : None  }

                tree.insert( '', key, item, [], icon = folder_icon)

    window.Element( tree_key ).update(values = tree )
    window.Element( tree_key ).Widget.configure(show='tree')  # Hide header

# ------------------------------------------------
#   WRW 14 Jan 2022 - Change to store path relative to root_path in tree and aux
#       and remove pathlib. It looks fine but it is not what I have used elsewhere
#       and was causing confusion.
#   WRW 16 Jan 2022 - Studied pathlib and will likely migrate to it.
#   WRW 5 Mar 2022 - Remove extensions. Build in just '.pdf'. OK after lower().
#       Oops, added back in. This used for audio and music.

def add_to_browse_tree( tree_key, tree, aux, parent_key, node, root_path, file_icon, extensions ):

    node['children'] = []
    parent_path = os.path.join( node['relpath'], node['file'] )
    items = sorted( os.listdir( os.path.join( root_path, parent_path )) )

    for item in items:
        key = new_key( aux )
        relpath = os.path.join( parent_path, item )

        if os.path.isdir( os.path.join( root_path, relpath ) ):
            kind = 'dir'
            icon = folder_icon 

        else:
            kind = 'file'
            _, ext = os.path.splitext( item )
            if ext.lower() not in extensions:
                continue
            icon = file_icon

        tree.insert( parent_key, key, item, [], icon = icon )

        node['children'].append(key)
        aux[key] = { 'kind' : kind,
                     'relpath' : parent_path,
                     'file' : item,
                     'children' : None
                    }

    tree_element = window.Element( tree_key )
    tree_element.update( values=tree )

    iid = tree_element.KeyToID[parent_key]
    tree_element.Widget.item( iid, open=True )
    tree_element.Widget.see( iid )

# ------------------------------------------------
#   Select one title of several based on priority of 'src'. Any need to consider composer?
#   No, but do have to consider canonical.
#   /// RESUME - better way to do this?

#   Data: [[ title, composer, cpage, page, src, local, canonical, file ]]

def select_by_src_priority( data ):
    titles = {}
    results = []

    for row in data:
        title = row[0]
        canonical = row[7]

        #   This took a few minutes, better than doing it explicitly as commented out?

        titles[ title ] = titles.setdefault( title, {} )
        titles[ title ][ canonical ] = titles[ title ].setdefault( canonical, [] )
        titles[ title ][ canonical ].append( row )

        # if not title in titles:
        #     titles[ title ] = {}
        # if not canonical in titles[ title ]:
        #     titles[ title ][ canonical ] = []
        # titles[ title ][ canonical ].append( row )

    for title in titles:
        for canonical in titles[ title ]:
            found = False
            for row in titles[ title ][ canonical ]:
                for src in Source_Priority:
                    if row[ 5 ] == src:
                        found = True
                        results.append( row )
                        break
                if found:
                    break

    return results

# -----------------------------------------------------------------------
#   No priority now, just return first from canonical list.

def select_by_canonical_priority( data ):
    titles = {}
    results = []

    for row in data:
        title = row[0]
        canonical = row[7]

        titles[ title ] = titles.setdefault( title, {} )
        titles[ title ][ canonical ] = titles[ title ].setdefault( canonical, [] )
        titles[ title ][ canonical ].append( row )

    for title in titles:
        for canonical in titles[ title ]:
            row = titles[ title ][ canonical ][0]
            results.append( row )
            break

    return results

# -----------------------------------------------------------------------

def do_profile( dc ):

    res = []
    window.Element( 'tab-results-table' ).select()
    window['tab-results-table'].update( visible = True )

    query = "SHOW PROFILE CPU, BLOCK IO"
    dc.execute( query )
    rows = dc.fetchall()
    for row in rows:
        res.append( [row['Status'], row['Duration']] )

    window.Element( 'results-table' ).update( values=res )

# -----------------------------------------------------------------------

def do_query_music_file_index_with_join( dc, title, composer, lyricist, album, artist, src, canonical ):

    # window.set_cursor( "clock" )      # looks terrible. With my own FULLTEXT don't need any 'busy' indicator.
    # window.refresh()

    table = []
    data = []
    wheres = []
    count = 0

    # query = "SET PROFILING = 1"
    # dc.execute( query )

    if title:
        if MYSQL:
            wheres.append( "MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""titles_distinct_fts.title MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "titles_distinct.title", title )
                wheres.append( w )
                data.extend( d )

    if composer:
        if MYSQL:
            wheres.append( "MATCH( composer ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( composer )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""composer MATCH ?""" )
                data.append( composer )
            else:
                w, d = fb.get_fulltext( "composer", composer )
                wheres.append( w )
                data.extend( d )

    if lyricist:
        if MYSQL:
            wheres.append( "MATCH( lyricist ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( lyricist )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""lyricist MATCH ?""" )
                data.append( lyricist )
            else:
                w, d = fb.get_fulltext( "lyricist", lyricist )
                wheres.append( w )
                data.extend( d )

    if src:
        if MYSQL:
            wheres.append( "titles.src = %s" )
            data.append( src )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""titles.src MATCH ?""" )
                data.append( src )
            else:
                w, d = fb.get_fulltext( "titles.src", src )
                wheres.append( w )
                data.extend( d )

    if canonical:
        if MYSQL:
            wheres.append( "MATCH( local2canonical.canonical ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( canonical )
        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""local2canonical.canonical MATCH ?""" )
                data.append( canonical )
            else:
                w, d = fb.get_fulltext( "local2canonical.canonical", canonical )
                wheres.append( w )
                data.extend( d )

    if album:
        if MYSQL:
            wheres.append( """titles_distinct.title IN
                                   ( SELECT title FROM audio_files
                                     WHERE MATCH( album ) AGAINST( %s IN BOOLEAN MODE ) )
                           """ )
            data.append( album )

        if SQLITE:
            if FULLTEXT:
                wheres.append( """titles_distinct.title IN
                    ( SELECT title FROM audio_files
                      WHERE album MATCH ? ) """ )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "album", album )
                wheres.append( f"""titles_distinct.title IN
                                   ( SELECT title FROM audio_files WHERE {w} )
                                """ )
                data.extend( d )

    if artist:
        if MYSQL:
            wheres.append( """titles_distinct.title IN
                               ( SELECT title FROM audio_files
                                 WHERE MATCH( artist ) AGAINST( %s IN BOOLEAN MODE ) )
                           """ )
            data.append( artist )

        if SQLITE:
            if FULLTEXT:
                wheres.append( """titles_distinct.title IN
                    ( SELECT title FROM audio_files
                      WHERE artist MATCH ? ) """ )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "artist", artist )
                wheres.append( f"""titles_distinct.title IN
                                   ( SELECT title FROM audio_files WHERE {w} )
                                """ )
                data.extend( d )


    # -----------------------------------------------------------------------
    #   WRW 24 Feb 2022 - I think I screwed up 'include_titles_missing_file' settings considering
    #       it for local2canonical instead of canonical2file.

    if len( data ):
        where_clauses = "WHERE " + " AND ".join( wheres )

        if False:
            canonical2file_join = 'JOIN canonical2file USING( canonical )'
            if conf.val( 'include_titles_missing_file' ):
                local2canonical_join = 'LEFT JOIN local2canonical USING( local, src )'
            else:
                local2canonical_join = 'JOIN local2canonical USING( local, src )'

        else:
            local2canonical_join = 'JOIN local2canonical USING( local, src )'
            if conf.val( 'include_titles_missing_file' ):
                canonical2file_join = 'LEFT JOIN canonical2file USING( canonical )'
            else:
                canonical2file_join = 'JOIN canonical2file USING( canonical )'

        if MYSQL:
            query = f"""
                SELECT titles_distinct.title, titles.composer, titles.sheet, titles.src, titles.local,
                local2canonical.canonical, canonical2file.file
                FROM titles_distinct
                JOIN titles USING( title_id )
                {local2canonical_join}
                {canonical2file_join}
                {where_clauses}
                ORDER BY titles_distinct.title, local2canonical.canonical, titles.src   
                LIMIT {Select_Limit}
            """

        # ---------------------------------------------------------------------------
        #   This was a real pain to get working. Turns out that fullword search in sqlite3 can't
        #   have an ORDER BY clause for anything bu rank, at least that's what appears to be the
        #   case from some toy tests.

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT titles_distinct_fts.title,
                    titles.composer, titles.sheet, titles.src, titles.local,
                    local2canonical.canonical, canonical2file.file
                    FROM titles_distinct_fts
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {canonical2file_join}
                    {where_clauses}
                    ORDER BY rank
                    LIMIT {Select_Limit}
                """

            else:
                query = f"""
                    SELECT titles_distinct.title,
                    titles.composer, titles.sheet, titles.src, titles.local,
                    local2canonical.canonical, canonical2file.file
                    FROM titles_distinct
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {canonical2file_join}
                    {where_clauses}
                    ORDER BY titles_distinct.title, local2canonical.canonical, titles.src   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

        # if True:
        if False:
            print( "Query", query )
            print( "Data", data )

        dc.execute( query, data )
        rows = dc.fetchall()

        # headings = [ "Title", "Composer", "Canonical Book Name", "Page", "Sheet", "Source", "Local Book Name", "File" ],

        if rows:
            for row in rows:
                title = row[ 'title' ]
                composer = row[ 'composer' ]
                canonical = row[ 'canonical' ]
                sheet = row[ 'sheet' ]
                src = row[ 'src' ]
                file = row[ 'file' ]
                local = row[ 'local' ]
                # cpage = fb.adjust_page( dc, page, src, local, title, False )
                page = fb.get_page_from_sheet( sheet, src, local )

                table.append( [ title, composer, canonical, page, sheet, src, local, file ] )

        if MYSQL:
            query = f"""
                SELECT count(*) cnt
                FROM titles_distinct
                JOIN titles USING( title_id )
                {local2canonical_join}
                {where_clauses}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT count(*) cnt
                    FROM titles_distinct_fts
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {where_clauses}
                """
            else:
                query = f"""
                    SELECT count(*) cnt
                    FROM titles_distinct
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {where_clauses}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    # window.set_cursor( "arrow" )
    return (table, count)

# --------------------------------------------------------------------------

def do_query_music_file_index( dc, title, composer, lyricist, src, canonical ):
    return do_query_music_file_index_with_join( dc, title, composer, lyricist, None, None, src, canonical )

# --------------------------------------------------------------------------
#   WRW 19 Feb 2022 - Toyed around with searching filename in audio_files
#       but don't think it is a good idea. Nothing in filename not already
#       in the metadata

#   wheres.append( "MATCH( file ) AGAINST( %s IN BOOLEAN MODE )" )
#   data.append( title )

#   wheres.append( f"""file MATCH ?""" )
#   data.append( title )

#   w, d = fb.get_fulltext( "file", title )
#   wheres.append( w )
#   data.extend( d )

def do_query_audio_files_index( dc, title, album, artist ):
    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""title MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "title", title )
                wheres.append( w )
                data.extend( d )

    if album:
        if MYSQL:
            wheres.append( "MATCH( album ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( album )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""album MATCH ?""" )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "album", album )
                wheres.append( w )
                data.extend( d )

    if artist:
        if MYSQL:
            wheres.append( "MATCH( artist ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( artist)

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""artist MATCH ?""" )
                data.append( artist )
            else:
                w, d = fb.get_fulltext( "artist", artist )
                wheres.append( w )
                data.extend( d )

    # ---------------------------------------------------

    if len( data ):
        where = "WHERE " + " AND ".join( wheres )

        if MYSQL:
            query = f"""
                SELECT title, artist, album, file
                FROM audio_files
                {where}
                ORDER BY title, artist   
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title, artist, album, file
                    FROM audio_files_fts
                    {where}
                    ORDER BY title, artist   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT title, artist, album, file
                    FROM audio_files
                    {where}
                    ORDER BY title, artist   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                title = row[ 'title' ]
                artist = row[ 'artist' ]
                album = row[ 'album' ]
                file = row[ 'file' ]
                table.append( [ title, artist, album, file ] )

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM audio_files
                {where}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM audio_files_fts
                    {where}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM audio_files    
                    {where}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_music_filename( dc, title ):

    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( rpath ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

            wheres.append( "MATCH( file ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""rpath MATCH ?""" )
                data.append( title )

                wheres.append( f"""file MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "rpath", title )
                wheres.append( w )
                data.extend( d )

                w, d = fb.get_fulltext( "file", title )
                wheres.append( w )
                data.extend( d )

    if len( data ):

        where = "WHERE " + " OR ".join( wheres )

        if MYSQL:
            query = f"""
                SELECT rpath, file
                FROM music_files
                {where}
                ORDER BY rpath, file
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT rpath, file
                    FROM music_files_fts
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT rpath, file
                    FROM music_files
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                rpath = row[ 'rpath' ]
                file = row[ 'file' ]
                table.append( [ rpath, file ] )

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM music_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM music_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM music_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_midi_filename( dc, title ):

    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( rpath ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( "rpath MATCH ?" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "rpath", title )
                wheres.append( w )
                data.extend( d )

                w, d = fb.get_fulltext( "file", title )     # /// RESUME - include this in above?
                wheres.append( w )
                data.extend( d )

    if len( data ):
        where = "WHERE " + " OR ".join( wheres )
        if MYSQL:
            query = f"""
                SELECT rpath, file
                FROM midi_files    
                {where}
                ORDER BY rpath, file   
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT rpath, file
                    FROM midi_files_fts
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT rpath, file
                    FROM midi_files
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            table = [ [ row[ 'rpath' ], row[ 'file' ] ] for row in rows ]

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM midi_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM midi_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM midi_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_youtube_index( dc, title ):

    table = []
    data = []
    count = 0

    if title:
        if MYSQL:
            query = f"""
                SELECT titles_distinct.title,
                title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                FROM titles_distinct
                JOIN title2youtube ON title2youtube.title_id = titles_distinct.title_id
                WHERE MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )
                ORDER BY titles_distinct.title, title2youtube.ytitle   
                LIMIT {Select_Limit}
            """
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title,
                    title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                    FROM titles_distinct_fts
                    JOIN title2youtube USING( title_id )
                    WHERE titles_distinct_fts.title MATCH ?
                    ORDER BY titles_distinct.title, title2youtube.ytitle   
                    LIMIT {Select_Limit}
                """
                data.append( title )

            else:
                w, d = fb.get_fulltext( "titles_distinct.title", title )
                data.extend( d )

                query = f"""
                    SELECT title,
                    title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                    FROM titles_distinct
                    JOIN title2youtube USING( title_id )
                    WHERE {w}
                    ORDER BY titles_distinct.title, title2youtube.ytitle   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

    # --------------------------------------------------------------------

    if len( data ):
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                title = row[ 'title' ]
                ytitle = row[ 'ytitle' ]
                duration = row[ 'duration' ]
                yt_id = row[ 'yt_id' ]
                table.append( [ title, ytitle, duration, yt_id ] )

        # data = []
        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM titles_distinct
                JOIN title2youtube ON title2youtube.title_id = titles_distinct.title_id
                WHERE MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )
            """
            # data.append( title )

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM titles_distinct_fts
                    JOIN title2youtube USING( title_id )
                    WHERE titles_distinct_fts.title MATCH ?
                """
                # data.append( title )

            else:
                # w, d = fb.get_fulltext( "titles_distinct.title", title )
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM titles_distinct
                    JOIN title2youtube USING( title_id )
                    WHERE {w}
                """
                # data.extend( d )

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def make_boolean( val ):
    parts = val.split()
    t = [ '+' + x for x in parts ]
    val = " ".join( t )
    return val

# --------------------------------------------------------------------------

#   "canonical2file",
#   "canonicals",
#   "local2canonical",
#   "sheet_offsets",
#   "title2youtube",

#   database_tables[ label, table, query ]

database_tables = [                                     # for show stats.
    [ "All Music Files", "music_files", None ],
    [ "Indexed Music Files", None, 
        """SELECT COUNT(*) cnt
           FROM (
                SELECT COUNT(*) FROM titles
                JOIN local2canonical USING( local, src )
                GROUP BY canonical
           ) AS sub
        """
    ],
    [ "Titles in Indexed Music Files", "titles", None ],
    [ "Distinct Titles in Indexed Music Files", "titles_distinct", None ],
    [ "Titles in Indexed Music Files With Composer", None,
        """SELECT COUNT(*) cnt
           FROM titles 
           WHERE composer IS NOT NULL
        """
    ],
    [ "Titles in Indexed Music Files With Lyricist", None,
        """SELECT COUNT(*) cnt
           FROM titles 
           WHERE lyricist IS NOT NULL
        """
    ],
    [ "Titles in Audio Files", "audio_files", None],
    [ "Titles in Audio Files With Artist", None,
        """SELECT COUNT(*) cnt
           FROM audio_files
           WHERE artist IS NOT NULL
        """
    ],
    [ "Titles in Audio Files With Album", None,
        """SELECT COUNT(*) cnt
           FROM audio_files
           WHERE album IS NOT NULL
        """
    ],
    [ "Titles in Midi Files", None,
        """SELECT COUNT(*) cnt
           FROM midi_files
        """
    ],
    [ "Titles in YouTube Files", None,
        """SELECT COUNT(*) cnt
           FROM title2youtube
        """
    ],
    [ "Distinct Titles in Indexed Music Files Matching Titles in YouTube Files", None,
        """SELECT COUNT(*) cnt
           FROM title2youtube
           JOIN titles_distinct USING( title_id )
        """
    ],
    [ "Distinct Titles in Indexed Music Files Matching Titles in Audio Files", None,
        """SELECT COUNT(*) cnt
           FROM titles_distinct
           JOIN audio_files USING( title );
        """
    ],
]

# --------------------------------------------------------------------------

def do_menu_canon2file( dc ):
    window.Element( 'tab-results-table' ).select()
    window['tab-results-table'].update( visible = True )

    res = []

    query = f'SELECT canonical, file FROM canonical2file ORDER BY canonical'

    dc.execute( query )
    for row in dc:
        res.append( [row['canonical'], row['file']] )

    window.Element( 'results-table' ).update( values=res )

# --------------------------------------------------------------------------

def do_menu_stats( dc ):

    window.Element( 'tab-results-table' ).select()
    window['tab-results-table'].update( visible = True )

    res = []

    # ------------------------

    res.append( ['', ''] )
  # res.append( [ sg.Text( 'Overall Statistics:', font=("Helvetica", 10, 'bold'), justification='right') , ''] )
    res.append( ['Overall Statistics:', ''] )

    for label, table, query in database_tables:

        if not query:
            query = f'SELECT COUNT(*) cnt FROM {table}'

        dc.execute( query )
        rows = dc.fetchall()

        for row in rows:
            res.append( [ f"   {label}", row['cnt']] )

    # ------------------------

    res.append( [ '', '' ] )
    res.append( ['Title Count by Index Source and Canonical Name from Indexed Music Files:', '' ] )

    query = f"""SELECT COUNT(*) cnt, src, canonical
        FROM titles
        JOIN local2canonical USING( local, src )
        GROUP BY canonical, src
        ORDER BY canonical, src
    """
    dc.execute( query )
    rows = dc.fetchall()

    for row in rows:
        res.append( [ f"   ({row['src']})   {row['canonical']}", row['cnt'] ] )

    # ------------------------

    res.append( [ '', '' ] )
    res.append( ['Title Count by Index Source:', ''] )

    query = 'SELECT COUNT(*) cnt, src FROM titles GROUP BY src ORDER BY src'

    dc.execute( query )
    rows = dc.fetchall()

    for row in rows:
        res.append( [ f"   {row['src']}", row['cnt']] )

    # ------------------------

    res.append( [ '', '' ] )
    res.append( ['Coverage of Canonical Book Names by Index Source:\n', ''] )

    query = "SELECT canonical, src FROM local2canonical ORDER BY canonical, src"
    dc.execute( query )

    results = {}
    rows = dc.fetchall()
    for row in rows:
        canon = row[ 'canonical' ]
        src = row[ 'src' ]

        if not canon in results:
            results[ canon ] = []

        results[ canon ].append( src )

    for canon in results:
        res.append( [ f"   {canon}", ' '.join( results[ canon ] )] )

    # ------------------------

    res.append( '\n' )
    res.append( ['Canonical Books Missing in Canonical2File Data:', '' ] )
    query = """SELECT canonical, file FROM canonicals
            LEFT JOIN canonical2file USING( canonical )
            WHERE file is Null
            """
    dc.execute( query )

    rows = dc.fetchall()
    for row in rows:
        res.append( [f"   {row['canonical']}",  '' ] )

    # ------------------------

    res.append( '\n' )
    res.append( ['Files in Canonical2File Data but not found in Music Library:', '' ] )

    query = """SELECT file FROM canonical2file
            """

    dc.execute( query )
    rows = dc.fetchall()
    found = False
    for row in rows:
        file = row['file']
        path = os.path.join( fb.Music_File_Root, file )
        if not os.path.isfile( path ) or not os.access( path, os.R_OK):
            res.append( [f"   {file}",  '' ] )
            found = True

    if not found:
        res.append( ['    None found', '' ] )

    # ------------------------

    window.Element( 'results-table' ).update( values=res )

    # ------------------------

# --------------------------------------------------------------------------
#   Looks like not used. DELETE

def OMIT_do_menu_stats_list( dc ):

    window.Element( 'tab-results-text' ).select()
    window['tab-results-text'].update( visible = True )
    window.Element( 'results-text' ).update( value='' )

    res = []

    # ------------------------

    res.append( '\n' )
    res.append( 'Overall Statistics:\n' )

    for label, table, query in database_tables:

        if not query:
            query = f'SELECT COUNT(*) cnt FROM {table}'

        dc.execute( query )
        rows = dc.fetchall()

        for row in rows:
            res.append( f"   {label}: {row['cnt']}" )

    # ------------------------

    res.append( '\n' )
    res.append( 'Titles by Indexed Music File:\n' )

    query = f"""SELECT COUNT(*) cnt, canonical
        FROM titles
        JOIN local2canonical USING( local, src )
        GROUP BY canonical
        ORDER BY canonical
    """
    dc.execute( query )
    rows = dc.fetchall()

    for row in rows:
        res.append( f"   {row['canonical']}: {row['cnt']}" )

    # ------------------------

    res.append( '\n' )
    res.append( 'Titles by Index Source:\n' )

    query = 'SELECT COUNT(*) cnt, src FROM titles GROUP BY src ORDER BY src'

    dc.execute( query )
    rows = dc.fetchall()

    for row in rows:
        res.append( f"   {row['src']}: {row['cnt']}" )

    # ------------------------
    res.append( '\n' )
    res.append( 'Coverage of Canonical Book Names by Index Source:\n' )

    query = "SELECT canonical, src FROM local2canonical ORDER BY canonical"
    dc.execute( query )

    results = {}
    rows = dc.fetchall()
    for row in rows:
        canon = row[ 'canonical' ]
        src = row[ 'src' ]

        if not canon in results:
            results[ canon ] = []

        results[ canon ].append( src )

    for canon in results:
        res.append( f"{canon}: { ' '.join( results[ canon ] ) }" )

    # ------------------------

    res = '\n'.join( res )
    window.Element( 'results-text' ).update( res )

    # ------------------------

# --------------------------------------------------------------------------
#   WRW 20 Mar 2022 - Add conn, c, dc to pass to external command so it
#       has DB connection and doesn't open and close another, which appeared
#       to close this one.

# extcmd_popen = None
window = None

def run_external_command( command ):                                                  
    global extcmd_popen

    window.Element( 'tab-results-text' ).select()
    window.Element( 'results-text' ).update( value='' )
    window['tab-results-text'].update( visible = True )

    # --------------------------------------------------------------------------
    #   WRW 15 Mar 2022 - Exploring running command as included package.
    #   /// RESUME make conditional on packaging type conf.Package_Type.

    Command_as_Module = False
    Command_as_Module = True
    Debugging = True
    Debugging = False

    # --------------------------------------------------------------------------
    #   Run command as loadable module.
    #   click() in build_tables.py and check_offsets.py is exiting, not 
    #       returning back to program calling main().
    #       Work around by surrounding call with try/except SystemExit to catch exit.
    #   See: https://stackoverflow.com/questions/52740295/how-to-not-exit-a-click-cli
    #   WRW 22 Mar 2022 - Remove try/excep SystemExit on call build_tables and check_offsets.
    #       Confirmed click() was exiting.
    #       Added 'standalone_mode=False' to do_main() call in commands. Confirmed click()
    #       was not exiting. Problem solved. Now picking up rcode.

    if Command_as_Module:

        if not Debugging:
            window[ 'results-text' ].reroute_stdout_to_here()
            window[ 'results-text' ].reroute_stderr_to_here()

        if command[0] == 'bl-build-tables':
            import build_tables
            rcode = build_tables.aux_main( command )

        elif command[0] == 'bl-check-offsets':
            import check_offsets
            rcode = check_offsets.aux_main( command )

        window[ 'results-text' ].restore_stdout()
        window[ 'results-text' ].restore_stderr()

        if rcode:
            window['results-text' ].print( f"\nCommand failed, { ' '.join( command )} returned exit code: {rcode}" )
        else:
            window['results-text' ].print( f"\nCommand completed successfully." )

    # --------------------------------------------------------------------------
    #   Run command as external process.

    else:
        if extcmd_popen:
            extcmd_popen.kill()
            extcmd_popen = None

        extcmd_popen = subprocess.Popen( command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True )
        for line in extcmd_popen.stdout:
            window[ 'results-text' ].print( line, end='' )

        extcmd_popen.stdout.close()
        rcode = extcmd_popen.wait()

        # --------------------------------------------------------------------------

        if rcode:
            window['results-text' ].print( f"\nCommand failed, { ' '.join( command )} returned exit code: {rcode}" )

        else:
            window['results-text' ].print( f"\nCommand completed successfully." )


# --------------------------------------------------------------------------

def do_show_recent_log():
    res = ''
    window.Element( 'tab-results-text' ).select()
    window['tab-results-text'].update( visible = True )
    for ev, va in fb.get_log():
        res += f"{ev:>50}: {va}\n"

    window.Element( 'results-text' ).update( value=res )

# --------------------------------------------------------------------------

def do_show_recent_event_histo():
    res = ''
    window.Element( 'tab-results-text' ).select()
    window['tab-results-text'].update( visible = True )

    res += f"{'Event':>60}{'Value':>10}: Count\n"
    histo = fb.get_log_histo()
    for ev in sorted( histo.keys()):
        res += f"{ev:>60}\n"

        for va in sorted( histo[ ev ].keys()):
            res += f"{va:>70}: {histo[ev][va]}\n"

    window.Element( 'results-text' ).update( value=res )

# --------------------------------------------------------------------------
#   Playing around with mouse motion. Function didn't get called.
#   Got an event instead.

# window['indexed-music-file-table'].bind( '<Motion>', mouse_motion )
# def mouse_motion( event ):
#     print( f"Mouse: {event.x}, {event.y}" )

# --------------------------------------------------------------------------
#   WRW 20 Jan 2022 - Move initialization into separate function so can
#       easily test timeout if needed.
#   Initialization that was in Initial EVENT Loop, triggered by timeout.
#   With window.finalize() looks like don't need to wait for timeout event.
#   Nope, definitely need it. Realized it when migrated to fb_pdf() approach.
#   Looks like timing sensitive. Size of graph element will now be valid here.
#   And we can shoe initial pdf file.

#   window.Element( 'tab-display-pdf' ).select()
#   window.Element( 'tab-display-pdf' ).set_focus()
#   window.Element( 'display-graph-pdf' ).draw_line( (0,0), (100,100)  )

def initialize_gui( dc, window ):
    global music_tree, audio_tree

    # -------------------------------------------------------
    #   Load Help file into PDF viewer for initial display.
    #   This needed to get graph size of Graph element established early for some reason.
    #   Must call previously call finalize() for this to work. That may have been only
    #   issue with initialization as size now OK without this.

    pdf.show_music_file( file=fb.get_docfile(), page=1, force=True )    # Initial display
    meta.show( id='Initial',
               file=fb.get_docfile(),
               page=1,
               page_count = 1,
               title='Bluebird Music Manager', )

    toc.show()

    # size = window.Element( 'display-graph-pdf' ).get_size()

    # -------------------------------------------------------
    #   Load initial data into music and audio browse trees (in left sidebar).

    music_tree = sg.TreeData()
    initialize_browse_tree( 'browse-music-files', music_tree, music_tree_aux, fb.Music_File_Folders, fb.Music_File_Root )
    
    audio_tree = sg.TreeData()
    initialize_browse_tree( 'browse-audio-files',  audio_tree, audio_tree_aux, fb.Audio_Folders, fb.Audio_File_Root )
    
    # -------------------------------------------------------
    #   Set focus to title search box and select pdf display, which now contains help file.

    window.Element( 'song-title' ).set_focus()
    window.Element( 'tab-display-pdf' ).select()
    
    # -------------------------------------------------------
    #   Set saved values for setlist in both setlist Combo elements.
    
    current_name = sl.setlist_load()
    sl_names = sl.setlist_get_names()
    window.Element(  'setlist-save-menu' ).update( values = sl_names, value=current_name )
    window.Element(  'setlist-controls-menu' ).update( values = sl_names, value=current_name )
    
    # --------------------------------------------
    #   Load current setlist in setlist tab.
    #   /// this causing extraneous setlist event.
    
    sl.setlist_show( current_name )
    
    # --------------------------------------------
    #   Pickup up resize of window, moved this from first pass through main event loop.
    #   Just bind to pdf display, not entire window, not sure why, likely to reduce
    #   number of events during startup.

    #   According to the official tk documentation, <Configure> events fire
    #   "whenever its size, position, or border width changes, and sometimes when
    #   it has changed position in the stacking order." This can happen several
    #   times during startup.

    #   Note: Config-Event processed in fb_pdf.py, not here. Appears as 'display-graph-pdf-Config-Event'
    
    # window.bind( '<Configure>', 'Config-Event' )    # size of widget changed
    window.Element( 'display-graph-pdf' ).bind( '<Configure>', '-Config-Event' )    # size of widget changed

    # --------------------------------------------
    #   Set the visibility of some tabs based on config option.

    set_index_mgmt_visibility( ShowIndexMgmgTabs )

    # --------------------------------------------------------------------------
    #   Drop down to Tkinter to control the tabgroups. Need fill and expand for this not PSG expand_x, expand_y.
    #   This was an incredible pain to learn that fill is needed to get main tab bar to fill all available X space.
    #   The expand arg here overrides PySimpleGui expand_x and expand_y.
    #   See dummy exploration program "Play/expand-problem.py" for more details.
    
    window.Element( 'sidebar-tabgroup' ).Widget.pack( side = tk.LEFT, expand=False, fill=tk.Y )
    window.Element( 'main-tabgroup' ).Widget.pack( side = tk.LEFT, expand=True, fill=tk.BOTH )
    window.set_alpha(1)     # Show window. It had been initialized with alpha of 0.
    
# --------------------------------------------------------------------------

def select_pdf_tab():
    if not UseExternalMusicViewer:
        window.Element( 'tab-display-pdf' ).select()
        window.Element( 'display-graph-pdf' ).set_focus()

# --------------------------------------------------------------------------
#   Want more than can do in simple popup.
#   Show: Help->About Birdland
#   WRw 21 Mar 2022 - Pulled out into separate function to use with verbose, too.

def get_about_data():

    uname = os.uname()

    try:
        version = importlib.metadata.version( 'birdland' )
    except:
        try:
            version = importlib.metadata.version( 'birdland-wrwetzel' )
        except:
            version = 'not available'

    # ----------------------------------
    if SQLITE:
        database = f"SqLite3, Database File: {Path( conf.home_confdir, conf.sqlite_database)}"
    if MYSQL:
        database = f"MySql, Database: '{conf.mysql_database}'"

    # ----------------------------------
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        run_environment = f"PyInstaller bundle"

    elif "__compiled__" in globals():
        run_environment = f"Nuitka bundle"

    else:
        run_environment = f"Python process"

    try:
        timestamp = datetime.datetime.fromtimestamp( Path(sys.executable).stat().st_mtime ).strftime( '%a, %d-%b-%Y, %H:%M:%S')
    except:
        timestamp = f"not available for {sys.executable}"

    # ----------------------------------
    # Python Paths: {', '.join( [ x for x in sys.path ]) }
    # ----------------------------------
    info_text = f"""
    System:
        Sysname: {uname.sysname}
        Nodename: {uname.nodename}
        Release: {uname.release}
        Version: {uname.version}
        Machine: {uname.machine}

    Python:
        Python Version:  {platform.python_version()}
        PySimpleGui Version: {sg.__version__}
        TkInter Version: {sg.tclversion_detailed}
        Sqlite Version: {sqlite3.sqlite_version}
        Sqlite Python Module Version: {sqlite3.version}
        Fitz Module Version: {', '.join( fitz.version )}
        ConfigObj Module Version: {configobj.__version__}
        MySQLdb Module Version: {'.'.join([str(x) for x in MySQLdb.version_info ])}

    Birdland:
        Version: {version}
        Run Environment: {run_environment}
        Package Type: {conf.Package_Type}
        Executable Timestamp: {timestamp}
        Database: {database}

    Directories:
        Settings Directory: {conf.confdir}
        Program Directory: {conf.program_directory}
        Data Directory: {conf.data_directory}

    Executable Identity:
        Executable: {sys.executable}
        Argv[0]: {sys.argv[0]}
        __file__: {__file__}
    """
    return version, info_text

# --------------------------------------------------------------------------

def do_about():
    version, info_text = get_about_data()
    about_layout = [ 
        [
            sg.Image( source=BL_Icon, subsample=1, key='about-image', pad=((20,0),(20,0)) ),
            # sg.Image( source="Icons/Saxophone_128.png", subsample=1, key='about-image', pad=((20,0),(20,0)) ),
            sg.Text( fb_layout.Bluebird_Program_Title, pad=((20,20),(20,0)), font=("Helvetica", 20, "bold"), text_color='#e0e0ff' ),
        ],
        [
            sg.Text( f"Version: {version}", pad=((20,20),(10,0)), font=("Helvetica", 16, ), text_color='#e0e0ff' ),
        ],
        [
            sg.Text( f"Copyright \xa9 2022 Bill Wetzel", pad=((20,20),(8,0)), font=("Helvetica", 10, ), text_color='#e0e0ff' ),
        ],
        [
            sg.Text( f"This software and index data is released under the terms of the MIT License.", pad=((20,20),(2,0)), font=("Helvetica", 10, ), text_color='#e0e0ff' ),
        ],
        [
            sg.Multiline( info_text,
                    font=("Helvetica", 10 ),
                    pad=((20,20),(10,0)),
                    size = ( None, info_text.count( '\n' ) +1 ),
                    write_only = True,
                    # auto_refresh = True,
                    no_scrollbar = True,
                    expand_x = True,
                    # expand_y = True,
            )
        ],
        [
            sg.Button('Close', key='config-button-cancel', font=("Helvetica", 9), pad=((5,0),(10,10)), )
        ]
    ],

    # -------------------------------------------------------------

    about_window = sg.Window( 'About Birdland',
                        return_keyboard_events=False,
                        resizable=True,
                        icon=BL_Icon,
                        finalize = True,
                        layout=about_layout,
                        keep_on_top = True,
                       )

    about_window['about-image'].set_focus()

    # --------------------------------------------------------------------------
    #   EVENT Loop for About window.

    while True:
        event, values = about_window.Read( )

        if event == sg.WINDOW_CLOSED:
            return False

        elif event == 'config-button-cancel':
            about_window.close()
            return False

# --------------------------------------------------------------------------

@click.command()
@click.option( "-v", "--verbose", is_flag=True,         help="Show system info and media activity" )
@click.option( "-V", "--very_verbose", is_flag=True,    help="Show events" )
@click.option( "-c", "--confdir",                       help="Use alternate config directory" )
@click.option( "-d", "--database",                      help="Use database sqlite or mysql, default sqlite", default='sqlite' )
@click.option( "-p", "--progress", is_flag=True,        help="Show initialization progress" )
@click.option( "-l", "--log",      is_flag=True,        help="Capture logging data" )
@click.option( "-r", "--record",                        help="Record user interactions" )
@click.option( "-R", "--playback",                      help="Playback user interactions" )

def do_main( verbose, very_verbose, confdir, database, progress, log, record, playback ):

    logging = True if log else False

    # -----------------------------------------------------------------------
    #   A few exit and error functions defined inside main() for namespace reasons.

    def do_full_exit( code ):                                                           
        fb.stop_audio_file()
        fb.close_youtube_file()
        pdf.close()
        window.Close()
        if conn:
            conn.close()
        if record:
            recorder.save()
        sys.exit( code )

    def do_short_exit( code ):
        window.Close()
        if conn:
            conn.close()
        if record:
            recorder.save()
        sys.exit(code)

    def do_error_exit( text, values ):
        print( text, file=sys.stderr )
        for x in sorted( values ):
            print( f"{x:>30}: {values[x]}", file=sys.stderr )
        if record:
            recorder.save()
        do_full_exit( 1 )

    def do_error_announce( text, value ):
        fb.log( text, value )
        # beepy.beep(1)                                     # No longer, served it purpose while debugging.
        # window[ 'warning-icon' ].update( visible=True )   # Likewise
        do_show_recent_log()

    # -----------------------------------------------------------------------

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
        sys.exit(1)

    # ---------------------------------------------------------------
    #   Show about data after above DB constants are set.

    if verbose:
        print( get_about_data()[1] )

    # ------------------------------------------------------------------------------------------------------

    fb.set_driver( MYSQL, SQLITE, False )
    conf.set_driver( MYSQL, SQLITE, False )
    meta.set_driver( MYSQL, SQLITE, False )

    conf.set_icon( BL_Icon )
    conf.set_classes( sg )

    # ---------------------------------------------------------------
    #   Run birdland in the directory where the program lives for access
    #   to program modules, Icons and other related files. 

    #   Birdland running in conf.program_directory
    #   Data files are indicated by conf.data_directory

    #   WRW 10 Mar 2022 - A issue when running from PyInstaller packaged location with chdir here.
    #       cwd is fine when main() called from PyInstaller-packaged location.
    #       Change it only if called unbundled.
    #   /// RESUME - think about this some more. I prefer calling script set this up.

    if conf.Package_Type == 'Development' or conf.Package_Type == 'Setuptools':
        os.chdir( os.path.dirname(os.path.realpath(__file__)))

    # conf.set_install_cwd( os.getcwd() )

    # -----------------------------------------------------------------------
    #   Some simple tests of configuration. First half can be done before get_config().

    announce = 0

    results, success = conf.check_home_config( confdir )
    if not success:
        if progress:
            print( f"ERROR: Error in home configuration:", file=sys.stderr )
            print( '\n'.join( results ))
        conf.initialize_home_config( confdir )      # Need confdir to test if should have .birdland in home dir.
        announce += 1

    results, success = conf.check_specified_config( confdir )
    if not success:
        if progress:
            print( f"ERROR: Error in specified configuration:", file=sys.stderr )
            print( '\n'.join( results ))
        conf.initialize_specified_config( confdir )
        announce += 1

    # -----------------------------------------------------------------------
    #   Now load the configuration data.

    conf.get_config( confdir )

    # -----------------------------------------------------------------------
    #   WRW 3 Mar 2022 - Check for a config 'Host' section for hostname after get_config()
    #       but before anything using the config.

    results, success = conf.check_hostname_config()
    if not success:
        if progress:
            print( f"ERROR: Error in host-specific configuration:", file=sys.stderr )
            print( '\n'.join( results ))
        conf.initialize_hostname_config()
        announce += 1

    # -----------------------------------------------------------------------
    #   /// RESUME  Do this elsewhere, too, after get_config is called?

    conf.set_class_variables()

    # -----------------------------------------------------------------------
    #   Need conf class set up early. Do others at same time.

    fb.set_classes( conf )
    pdf.set_classes( conf )
    meta.set_classes( conf, fb, pdf )
    sl.set_classes( conf, sg, fb, pdf, meta, toc )
    mgmt.set_classes( conf, fb, pdf, meta, toc )
    diff.set_classes( conf, sg, fb, pdf, meta, toc )
    l2c.set_classes( conf, fb, pdf, meta, toc )
    c2f.set_classes( conf, fb, pdf, meta, toc )

    # -----------------------------------------------------------------------
    #   Set up class-specific configuration options. Uses self.class.vals... in each class.

    fb.set_class_config()
    pdf.set_class_config( )
    sl.set_class_config( )
    mgmt.set_class_config( )
    l2c.set_class_config( )
    c2f.set_class_config( )
    set_local_config( )

    # -----------------------------------------------------------------------

    if announce:
        conf.report_progress()

    # -----------------------------------------------------------------------
    #   Need a user and password for MySql. On initial startup will not have it.

    #   Some more simple tests of configuration.
    #   Second half must be done after get_config() as it may need DB credentials and other config data.
    #   May already have database in confdir under certain circumstances:
    #       Specified confdir at first execution, then none on later execution so using home confdir.

    results, success = conf.check_database( database )
    if not success:
        res = True
        if progress:
            print( f"ERROR: Error in database configuration:", file=sys.stderr )
            print( '\n'.join( results ))

        conf.initialize_database( database )

        if MYSQL:       # If check_database() failed for mysql it is likely because of user credentials.
            res = conf.get_user_and_password( )

            if res:
                conf.initialize_database( database )        # Try again with updated user/password.

            else:
                print( "ERROR: Can't continue without user credentials for MySql database", file=sys.stderr )
                exit(1)

    # -----------------------------------------------------------------------

    global window
    global music_tree
    global music_tree_aux
    global audio_tree
    global audio_tree_aux

    # -----------------------------------------------------------------------
    #   Initialize these early in case joker clicks on blank line in table coming from initial values of "".
    #   Not an issue, now initialized without blank line.

    # indexed_music_file_file_table_data = audio_file_table_data = \
    #     midi_file_table_data = youtube_file_table_data = music_file_table_data = []

    # -----------------------------------------------------------------------
    #   Prepare connection to database.
    #   fb_utils needs dc before get_layout()

    have_db = False

    # -----------------------------------------------
    if MYSQL:
        try:
            conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
            c = conn.cursor()
            dc = conn.cursor(MySQLdb.cursors.DictCursor)
            have_db = True

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on connect() or cursor(), type: {extype}, value: {value}", file=sys.stderr )

    # -----------------------------------------------
    elif SQLITE:
        def trace_callback( s ):                                      # Helpful for debugging
            print( "Trace Callback:", s )

        if Path( conf.home_confdir, conf.sqlite_database ).is_file():
            try:
                conn = sqlite3.connect( Path( conf.home_confdir, conf.sqlite_database ))      # This will create file if not exists. Can't use it to test for existence.
              # conn.set_trace_callback( trace_callback )
                c = conn.cursor()
                dc = conn.cursor()
                dc.row_factory = sqlite3.Row

            except Exception as e:
                (extype, value, traceback) = sys.exc_info()
                print( f"ERROR on connect() or cursor(), type: {extype}, value: {value}", file=sys.stderr )

            else:
                # conn.enable_load_extension(True)                  # Problem with fulltext caused by absence of this?
                # conn.load_extension("./fts3.so")                  # this doesn't exist.
                # c.execute( ".load /usr/lib/sqlite3/pcre.so" )     # This does not work, how load .so file. Perhaps this will be faster than my implementation.

                # sqlite3.enable_callback_tracebacks(True)          # This is very helpful for debugging

                # conn.create_function('regexp', 2, fb.regexp)        # This worked but not well. Perhaps with a little more work?
                # conn.create_function('my_match', 2, fb.my_match )   # This works great but is slower than LIKE.
                conn.create_function('my_match_c', 2, fb.my_match_c )   # This works great and is fast.
                have_db = True

    # -----------------------------------------------
    else:
        print( "ERROR-BUG: No database type specified", file=sys.stderr )
        sys.exit(1)

    # -----------------------------------------------
    #   Think about what to do here. I believe we should now always have a database by this point.

    if not have_db:
        print( "ERROR-BUG: Connect to database failed after initialization", file=sys.stderr )
        sys.exit(1)
        # conf.do_configure( first=True, confdir=confdir )
        # return

    # ----------------------------------

    fb.set_dc( dc )

    # ----------------------------------
    #   Possibly set theme - this doesn't work as well as setting a theme in the .config/... file?
    #       No, it looks OK now but I have some fixed colors that don't work well with the lighter themes.
    #   Theme preview:
    #       https://preview.redd.it/otneabe3zbz31.png?width=2305&format=png&auto=webp&s=7fdcf387d843f822892c724e0c6e73db038aec3d

    sg.theme( conf.val( 'theme' ) )

    # ----------------------------------
    #   Set the vertical window size to fill most of the vertical space.
    #   Horizongal size is fine as determined by layout.
    #   Don't use window.set_min_size((int(screen_x * .8), int(screen_y * .8)))
    #       since that does both X and Y. X is fine, just adjust Y to use most of the screen.

    screen_x, screen_y = sg.Window.get_screen_size()
    row_height = fb_layout.get_row_height()
    row_count = int( .8 * ( screen_y - (260+33) ) / row_height )
    fb_layout.set_row_count( row_count )

    layout = fb_layout.get_layout( sg, fb )     # Not a class yet so pass fb

    # ----------------------------------------------------
    #   Create the main window.

    window = sg.Window( fb_layout.Bluebird_Program_Title,
                        layout,     # Layout now all in separate file.
                        return_keyboard_events=True,
                        resizable=True,
                        icon=BL_Icon,
                        alpha_channel = 0,          # To keep window invisible until size stable.
                        use_default_focus = False,  # To keep c2f button from getting focus. Set it explicitly as needed. Not working?
                        finalize=True,
                       )               

    # ----------------------------------
    #   Show pdf control buttons only for built-in viewer.

    if UseExternalMusicViewer:
        window.Element('display-control-buttons' ).update( visible = False )
        window.Element('display-control-buttons' ).hide_row()
    else:
        window.Element('display-control-buttons' ).unhide_row()
        window.Element('display-control-buttons' ).update( visible = True )

    # ----------------------------------
    #   Select 'tab-display-pdf' so graph gets a size other than (1,1). This is all that is needed,
    #   no need to draw something on it, line, circle, non-scaled initial pdf file. Just do select().

    window.Element( 'tab-display-pdf' ).select()    

    #   Draw something, anything, on 'display-graph-pdf'. Nope, just have to select it.
    #   window.Element( 'display-graph-pdf' ).draw_circle( (200, 200), 75, fill_color = '#ff00ff', line_color = '#ff0000' )

    # ----------------------------------

    #   Pass some data to the supporting modules.
    #   /// RESUME - consider inheritance for this.

    # ---------------------
    fb.set_window( window )

    # ---------------------
    pdf.set_window( window )
    pdf.set_graph_element( window.Element( 'display-graph-pdf' ))

    # ---------------------

    status_bar = Status( window['status-bar'] )

    meta.set_elements(      # This allows the module to reference elements in the UI.
        window['display-page-title-exp'],
        window['display-page-local-exp'],
        window['display-page-canonical-exp'],
        window['display-page-file-exp'],
        window['display-page-number'],
        window['display-page-sheet'],
        window['current-audio-table'],
        window['current-midi-table'],
    )
    meta.set_dc( dc )
    meta.set_status( status_bar )

    # ---------------------
    toc.set_elements( fb, window['table-of-contents-table'] )

    # ---------------------
    sl.set_elements( 
                    window,
                    window['setlist-table'],
                    window['tab-display-pdf'],
                    window['setlist-move-up'],
                    window['setlist-move-down'],
                    window['setlist-delete'],
                    window['setlist-save-menu'],
                    window['setlist-controls-menu'],
                    window['tab-setlist-table'],
                  )

    sl.set_dc( dc )
    sl.set_icon( BL_Icon )

    # --------------------------------------------------------------

    mgmt.set_elements(      # This allows the module to reference elements in the UI.
        dc,
        window['index-mgmt-table'          ],
        window['index-mgmt-src-table'      ],
        window['index-mgmt-local-table'    ],
        window['index_mgmt_info_src'     ],
        window['index_mgmt_info_local'     ],
        window['index_mgmt_info_canonical'     ],
        window['index_mgmt_info_file'     ],
        window[ 'tab-display-pdf'       ],
        window[ 'index_mgmt_info_page_count'       ],
    )

    # --------------------------------------------------------------

    diff.set_elements(      # This allows the module to reference elements in the UI.
        dc,
        window[ 'index_diff_info_canonical'     ],
        window[ 'index-diff-table'          ],
        window[ 'index-diff-canonical-table'    ],
        window[ 'tab-display-pdf'       ],
    )

    diff.do_bind()
    diff.set_icon( BL_Icon )

    # ------------------------------------------------------------------------------------------------------

    l2c.set_elements(      # This allows the module to reference elements in the UI.
       dc,
       window['local2canonical-canonical-mgmt-table'],
       window['local2canonical-local-mgmt-table'],
       window['local2canonical-mgmt-src-combo'],
    )

    c2f.set_elements(      # This allows the module to reference elements in the UI.
       dc,
       window['canon2file-canonical-mgmt-table'],
       window['canon2file-link-mgmt-table'],
    )

    # --------------------------------------------------------------
    #   WRW 19 Mar 2022 - Deal with birdland.desktop file.

    fb_make_desktop.make_desktop( conf.Package_Type, verbose )

    # --------------------------------------------------------------
    #   Wait for timeout event then
    #   Otherwise it didn't show until got Config-Event.
    #   Moved body above. Works fine if call finalize() before.
    #   Probably don't need the size check any longer.
    #   Nope, this is needed. Only reason initial pdf appeared was because
    #   of multiple resize events. I don't want to depend on them.
    #   With nothing displayed in 'display-graph-pdf' this looped forever.

    #   Initial EVENT Loop. Move body into initialize function.
    #   Keep initial loop and timeout here is case need arises again.
    #   Need definitely arose. Only realized it with some instrumentation
    #   that showed multiple calls to show_pdf() because of Config events.
    #   Added limit while debugginb. Otherwise a pain to kill process.
    #   At some point in development the excss Config events stopped.
    # --------------------------------------------------------------

    # ========================================================================
    #   Initial EVENT loop. Wait for timeout event and size of graph to stabilize then initalize GUI.

    limit = 10
    counter = 0
    while counter < limit:
        event, values = window.Read( timeout = 10, timeout_key='timeout-event' )
        if logging:
            fb.log( event, values[ event ] if event in values else "-")
            fb.log_histo( event, values[ event ] if event in values else "-" )

        if event == 'timeout-event':
            size = window.Element( 'display-graph-pdf' ).get_size()
            # print( "Initial EVENT Loop size:", size )

            if size[0] > 1:
                break           # Had initialization in this area.

            counter += 1

        # ----------------------------------------------------
        #   Likely not needed but include be safe. In case user closes window during timeout loop.

        elif event == sg.WINDOW_CLOSED or event == 'Exit':
            do_short_exit(0)

    if counter == limit:
        print( f"ERROR-DEV: Initial EVENT Loop did not recognize valid size of 'display-graph-pdf' after {limit * 10} ms.", file=sys.stderr )
        do_short_exit(1)

    # print( f"DEBUG: Time needed for 'display-graph-pdf' to settle: {counter*10} ms."  )

    # ----------------------------------------------------
    #   Once have valid size for 'display-graph-pdf' can initialize gui. Size needed
    #   in that to scale initial pdf to fit size of graph.
    #   Postpone announcement of no database credentials till here, after window up.

    initialize_gui( dc, window )

    if record:
        recorder = Record( record )

    if playback:                              
        player = Record( playback )
        player.load()

    # ========================================================================
    #   WRW 7 Mar 2022 - added rudimentary record/play function for testing.
    #   Main EVENT Loop

    while True:
        if playback:
            event, values, last_sleep = player.get()
            _, _ = window.Read( timeout = last_sleep * 1000 )

        else:
            event, values = window.Read()

            if record:
                recorder.rec( event, values )

        # ------------------------------------------------------------------
        #   WRW - 15 Jan 2022 - Try moving this to the top. Working on error messages
        #       when close with 'X' button in window title. Yup, solved problem.
        #       NG when below "if '::' in event:". Must be above logging and verbose
        #       since event is None.

        if event == sg.WINDOW_CLOSED or event == 'Exit':
            do_full_exit(0)

        # ------------------------------------------------------------------

        if logging:
            if event not in [ 'MouseWheel:Down', 'MouseWheel:Up' ]:
                fb.log( event, values[ event ] if event in values else "-")
            fb.log_histo( event, values[ event ] if event in values else "-" )

        # fb.log( 'indexed_music_file_file_table_data',  len( indexed_music_file_file_table_data ) )
        # fb.log( 'music_file_table_data',               len( music_file_table_data ))
        # fb.log( 'audio_file_table_data',               len( audio_file_table_data ))
        # fb.log( 'youtube_file_table_data',             len( youtube_file_table_data ))

        if very_verbose:
            print( f"{'-'*60}" )
            print( "EVENT:", event )
            print( "VALUES:" )
            for x in sorted( values ): 
                print( f"{x:>30}: {values[x]}" )

            print()

        # ------------------------------------------------------------------
        #   Look for clicks in the menu bar at top of window. Do this up high, 
        #       before pdf.process_event(), which has "elif ':' in event".
        #       Menu elements include '::' between text and key.

        if '::' in event:
            t = event.split( '::' )
            if len( t ) == 2:
                menu_event = t[1]

                if menu_event == 'menu-about':
                    do_about()
                    continue

                elif menu_event == 'menu-tutorial':
                    pdf.show_music_file( file=fb.get_docfile(), page=1, force=True )        # Help in menu
                    meta.show( id='Help',
                               file=fb.get_docfile(),
                               page=1,
                               page_count = 1,
                               title='Bluebird Music Manager', )

                    toc.show()
                    select_pdf_tab()
                    continue

                elif menu_event == 'menu-configure':
                    saved = conf.do_configure()
                    if saved:
                        do_configure_save_update()
                    continue

                elif menu_event == 'menu-stats':
                    do_menu_stats( dc )
                    continue

                elif menu_event == 'menu-canon2file':
                    do_menu_canon2file( dc )
                    continue

                elif menu_event == 'menu-compare-pages':
                    run_external_command( [ 'bl-check-offsets', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    # run_external_command( [ 'check_offsets.py', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-all':
                    run_external_command( [ 'bl-build-tables', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    # run_external_command( [ 'build_tables.py', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-audio':
                    txt = """\nScanning your audio library may take a long time depending on size of your library.\n
                            Do you really want to do this?
                          """
                    t = conf.do_popup_ok_cancel( txt )
                    if t == 'OK':
                        run_external_command( [ 'bl-build-tables', '--scan_audio', '--audio_files', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                        # run_external_command( [ 'build_tables.py', '--scan_audio', '--audio_files', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-page-offset':
                    run_external_command( [ 'bl-build-tables', '--offset', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    # run_external_command( [ 'build_tables.py', '--offset', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-convert-raw-sources':
                    run_external_command( [ 'bl-build-tables', '--convert_raw', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    # run_external_command( [ 'build_tables.py', '--convert_raw', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                # elif menu_event == 'menu-test-db-times':
                #     do_menu_test_db_times()
                #     continue

                # --------------------------------------------------
                elif menu_event == 'menu-show-recent-log':
                    do_show_recent_log()
                    continue

                # --------------------------------------------------
                elif menu_event == 'menu-show-recent-event-histo':
                    do_show_recent_event_histo()
                    continue

                # --------------------------------------------------
                elif menu_event == 'menu-exit':
                    do_full_exit(0)

                # --------------------------------------------------
                elif menu_event == 'menu-index-mgmt-tabs':
                    toggle_index_mgmt_visibility()

                elif menu_event == 'menu-canon2file-tab':
                    toggle_canon2file_visibility()

                continue
            continue

        # ----------------------------------------------------------------
        #   Process events is the external classes.
        #   process_events() returns True if it procssed one, else False.
        #   This must be below '::' processing above.

        elif pdf.process_events( event, values ):
            continue

        elif sl.process_events( event, values ):
            continue

        elif mgmt.process_events( event, values ):
            continue

        elif diff.process_events( event, values ):
            continue

        elif meta.process_events( event, values ):
            continue

        elif l2c.process_events( event, values ):
            continue

        elif c2f.process_events( event, values ):
            continue

        # ------------------------------------------------------------------
        #   WRW 3 Mar 2022 - defer loading index management and related tables until tab activated.
        #   This prevents extraneous error messages on first launch before fully configured.
        #   User will only get error if screws around and clicks the tab before configuring.

        elif event == 'main-tabgroup':
            tab = values[ 'main-tabgroup' ]

            if tab == 'tab-canon2file-mgmt':
                window[ 'c2f-help' ].set_focus()        # This takes focus away from first element, a button.
                c2f.load_tables()
                continue

            elif tab == 'tab-local2canon-mgmt':
                l2c.load_tables()
                continue

            elif tab == 'tab-index-mgmt':
                mgmt.load_tables()
                continue

            elif tab == 'tab-index-diff':
                diff.load_tables()
                continue

        # ------------------------------------------------------------------

        elif event == 'stop-audio-youtube':
            fb.stop_audio_file()
            fb.close_youtube_file()
            continue

        # ----------------------------------------------------------------

        elif event == 'close-music':
            pdf.close_ext()
            continue

        # ----------------------------------------------------------------
        #   Search button or 'Enter' in search text boxes.
        elif event == 'search':

            # ---------------------------------------
            #   Gather search data

            title =                     values[ "song-title" ] if 'song-title' in values else None
            album =                     values[ "song-album" ] if 'song-album' in values else None
            artist =                    values[ "song-artist" ] if 'song-artist' in values else None
            composer =                  values[ "song-composer" ] if 'song-composer' in values else None
            lyricist =                  values[ "song-lyricist" ] if 'song-lyricist' in values else None
            src =                       values[ "local-src" ] if 'local-src' in values else None
            canonical =                 values[ "canonical" ] if 'canonical' in values else None
            join_flag =                 True if values[ 'search-join-title' ] else False
            search_multiple_src =       True if values[ 'search-multiple-src' ] else False
            search_multiple_canonical = True if values[ 'search-multiple-canonical' ] else False

            # ---------------------------------------
            #   Make MySql boolean search values.

            if MYSQL:
                if title:
                    title = make_boolean( title )
                if album:
                    album = make_boolean( album )
                if artist:
                    artist = make_boolean( artist )
                if composer:
                    composer = make_boolean( composer )
                if lyricist:
                    lyricist = make_boolean( lyricist )

            if SQLITE:      # /// RESUME - Anything to be done for search terms in Sqlite3?
                pass

            # ---------------------------------------
            #   Initialize all tables to no data. Update tables only when matched search selection.

            indexed_music_file_file_table_data = music_file_table_data = audio_file_table_data = \
                midi_file_table_data = youtube_file_table_data = []

            # ---------------------------------------
            #   Search music file index in database.
            #   Update indexed-music-file-table.

            tab_selected = False

            if join_flag:
                indexed_music_file_file_table_data, pdf_count = do_query_music_file_index_with_join( dc, title, composer, lyricist, album, artist, src, canonical )
            else:
                indexed_music_file_file_table_data, pdf_count = do_query_music_file_index( dc, title, composer, lyricist, src, canonical )

            if not search_multiple_src:
                indexed_music_file_file_table_data = select_by_src_priority( indexed_music_file_file_table_data )

            if not search_multiple_canonical:
                indexed_musicfile_file_table_data = select_by_canonical_priority( indexed_music_file_file_table_data )

            fb.safe_update( window['indexed-music-file-table'] , indexed_music_file_file_table_data, None )

            if len( indexed_music_file_file_table_data ):
                window.Element( 'tab-indexed-music-file-table' ).select()
                window.Element( 'tab-display-pdf' ).set_focus()
                tab_selected = True

            # ---------------------------------------
            #   /// RESUME - include additional search terms in do_query*() functions?
            #   Search music filename, audio file index, youtube index in database.
            #       Update associated tables.

            #   Select tab if search found any data going from left to right.
            #       Leave select/focus as is if nothing found.

            music_file_table_data, music_count = do_query_music_filename( dc, title )
            fb.safe_update( window['music-filename-table'], music_file_table_data, None )

            if len( music_file_table_data  ) and not tab_selected:
                window.Element( 'tab-music-filename-table' ).select()
                window.Element( 'tab-music-filename-table' ).set_focus()
                tab_selected = True

            # -----------------------
            audio_file_table_data, audio_count = do_query_audio_files_index( dc, title, album, artist )
            fb.safe_update( window['audio-file-table'], audio_file_table_data, None )

            if len( audio_file_table_data  ) and not tab_selected:
                window.Element( 'tab-audio-file-table' ).select()
                window.Element( 'tab-audio-file-table' ).set_focus()
                tab_selected = True

            # -----------------------
            #   WRW 8 Feb 2022 - Add support for midi files
            midi_file_table_data, midi_count = do_query_midi_filename( dc, title )
            fb.safe_update( window['midi-file-table'], midi_file_table_data, None )

            if len( midi_file_table_data  ) and not tab_selected:
                window.Element( 'tab-midi-file-table' ).select()
                window.Element( 'tab-midi-file-table' ).set_focus()
                tab_selected = True

            # -----------------------
            youtube_file_table_data, youtube_count = do_query_youtube_index( dc, title )
            fb.safe_update( window['youtube-file-table'], youtube_file_table_data, None )

            if len( youtube_file_table_data  ) and not tab_selected:
                window.Element( 'tab-youtube-table' ).select()
                window.Element( 'tab-youtube-table' ).set_focus()
                tab_selected = True

            # ------------------------------------------------------------
            #   Post result counts to status bar

            status_bar.set_music_index( pdf_count, len(indexed_music_file_file_table_data) )
            status_bar.set_audio_index( audio_count, len(audio_file_table_data) )
            status_bar.set_music_files( music_count, len(music_file_table_data) )
            status_bar.set_midi_files( midi_count, len(midi_file_table_data) )
            status_bar.set_youtube_index( youtube_count, len(youtube_file_table_data) )
            status_bar.show()

            continue

        # ======================================================================================
        #   Click in a row in one of the tables.
        #       index is row number in table. 
        #       values[ '...' ] is array of selected rows. Since we only
        #       select one at a time always use values[ '...' ][0]

        # ----------------------------------------------------------------
        #   Click in indexed music file table.
        #   WRW  28 Jan 2022 - Rearranged this slightly to match pattern of other table events.

        # headings = [ "Title", "Composer", "Page", "Sheet", "P=S", "Source", "Local Book Name", "Canonical Book Name", "File" ],

        elif event == 'indexed-music-file-table':
            if indexed_music_file_file_table_data:

                if "indexed-music-file-table" in values and len( values[ "indexed-music-file-table" ] ):
                    index = values[ "indexed-music-file-table" ][0]

                    title =     indexed_music_file_file_table_data[ index ][0]
                    canonical = indexed_music_file_file_table_data[ index ][2]
                    page =      indexed_music_file_file_table_data[ index ][3]
                    sheet =     indexed_music_file_file_table_data[ index ][4]
                    src   =     indexed_music_file_file_table_data[ index ][5]
                    local =     indexed_music_file_file_table_data[ index ][6]
                    file  =     indexed_music_file_file_table_data[ index ][7]

                    if not file:
                        sg.popup( f"\nNo music file available for:\n\n   '{title}'\n\n    Canonical: {canonical}\n",
                            title='Birdland Warning',
                            icon='BL_Icon',
                            line_width = 100,
                            keep_on_top = True,
                        )
                        continue

                    else:
                        path = Path( fb.Music_File_Root, file )

                        if not path.is_file():
                            conf.do_nastygram( 'music_file_root', path )
                            continue

                        else:
                            pdf.show_music_file( file=path, page=page )      # Click in Indexed Music File Table.
                            meta.show( id='IndexTable',
                                       file=file,
                                       title=title,
                                       canonical=canonical,
                                       sheet=sheet, 
                                       src=src,
                                       local=local, 
                                       page=page,
                                       page_count = pdf.get_info()[ 'page_count' ],
                                     )

                            toc.show( src=src, local=local )
                            select_pdf_tab()

                else:
                    do_error_announce( f"ERROR: Unexpected values content for 'indexed-music-file-table' event", values[ event ] )
            continue

        # ----------------------------------------------------------------
        #   Click in music file table.
        # headings = [ "Path", "File"  ],

        elif event == 'music-filename-table':
            if music_file_table_data:
                if "music-filename-table" in values and len( values[ "music-filename-table" ] ):
                    index = values[ "music-filename-table" ][0]

                    rpath = music_file_table_data[ index ][0]
                    file =  music_file_table_data[ index ][1]

                    fullpath = Path( fb.Music_File_Root, rpath, file )
                    if not fullpath.is_file():
                        conf.do_nastygram( 'music_file_root', fullpath )
                        continue

                    relpath = Path( rpath, file )

                    pdf.show_music_file( file=fullpath, page=1 )      # Click in Music File Table
                    meta.show( id='File Table',
                               file=relpath.as_posix(),
                               page=1,
                               page_count = pdf.get_info()[ 'page_count' ],   
                             )
                    toc.show( file=relpath )
                    select_pdf_tab()

                else:
                    do_error_announce( f"ERROR: Unexpected values content for 'music-filename-table' event", values[event] )
            continue

        # ------------------------------------------------------------
        #   Click in audio file table.
        # headings = [ "Title", "Artist", "Album", "File" ],

        elif event == 'audio-file-table':
            if audio_file_table_data:
                if "audio-file-table" in values and len( values[ "audio-file-table" ] ):
                    index = values[ "audio-file-table" ][0]

                    file = audio_file_table_data[ index ][3]
                    path = Path( fb.Audio_File_Root, file )

                    if not path.is_file():
                        conf.do_nastygram( 'audio_file_root', path )
                        continue

                    fb.play_audio_file( path )

                else:
                    do_error_announce( f"ERROR: Unexpected values content for 'audio-file-table' event", values[event] )
            continue

        # ----------------------------------------------------------------

        elif event == 'midi-file-table':
            if midi_file_table_data:
                if "midi-file-table" in values and len( values[ "midi-file-table" ] ):
                    index = values[ "midi-file-table" ][0]
                    path = midi_file_table_data[ index ][0]
                    file = midi_file_table_data[ index ][1]
                    fullpath = Path( fb.Midi_File_Root, path, file )

                    if not fullpath.is_file():
                        conf.do_nastygram( 'midi_file_root', fullpath )
                        continue

                    fb.play_midi_file( fullpath )

                else:
                    do_error_announce( f"ERROR: Unexpected values content for 'audio-file-table' event", values[event] )
            continue

        # ----------------------------------------------------------------
        #   Click in current audio table (in left sidebar)

        elif event == 'current-audio-table':
            if "current-audio-table" in values and len( values[ "current-audio-table" ] ):
                index = values[ "current-audio-table" ][0]

                table_data = window['current-audio-table'].get()    # Returns 2d array

                file = table_data[ index ][2]
                path = os.path.join( fb.Audio_File_Root, file )
                fb.play_audio_file( path )

            else:
                do_error_announce( f"ERROR: Unexpected values content for 'current-audio-table' event", values[event] )

            continue

        # ----------------------------------------------------------------
        #   Click in current midi table (in left sidebar)

        elif event == 'current-midi-table':
            if "current-midi-table" in values and len( values[ "current-midi-table" ] ):
                index = values[ "current-midi-table" ][0]
                table_data = window['current-midi-table'].get()    # Returns 2d array
                path = table_data[ index ][0]
                file = table_data[ index ][1]
                fullpath = os.path.join( fb.Midi_File_Root, path, file )

                if verbose:
                    print( "Playing midi:", fullpath )

                fb.play_midi_file( fullpath )
            else:
                do_error_announce( f"ERROR: Unexpected values content for 'current-midi-table' event", values[event] )

            continue

        # ----------------------------------------------------------------
        #   Click in YouTube file table
        # headings = [ "Title", "YT Title", "Duration", "yt_id" ],

        elif event == 'youtube-file-table':
            if youtube_file_table_data:
                if "youtube-file-table" in values and len( values[ "youtube-file-table" ] ):
                    index = values[ "youtube-file-table" ][0]

                    ytitle = youtube_file_table_data[ index ][1]
                    yt_id = youtube_file_table_data[ index ][3]

                    # fb.open_youtube_file( ytitle )
                    fb.open_youtube_file_alt( yt_id )

                else:
                    do_error_announce( f"ERROR: Unexpected values content for 'youtube-file-table' event", values[event] )
            continue

        # ----------------------------------------------------------------
        #   Click in book titles table (TOC) in left tab group.
        #   Remember, TOC displayed after PDF so already have music_file name and more.
        #

        elif event == 'table-of-contents-table':
            if 'table-of-contents-table' in values and len( values[ "table-of-contents-table" ] ):
                index = values[ "table-of-contents-table" ][0]
                sheet = toc.get_sheet( index )

                info = meta.get_info()
                src = info[ 'src' ]
                local = info[ 'local' ]
                page = fb.get_page_from_sheet( sheet, src, local )
                page_count = pdf.get_info()[ 'page_count' ]

                if int( page ) > page_count:
                    sg.popup( f"Index / Offset Error\n\n   Selected page exceeds pages in music file.\n",
                        line_width = 100,
                        keep_on_top = True,
                        title='Birdland Warning',
                        icon='BL_Icon',
                    )
                    continue

                file = Path( pdf.get_info()[ 'file' ] ).relative_to( fb.Music_File_Root ).as_posix()

                #   Update page. No toc.show() in this instance, that is already displayed.
                pdf.show_music_file( page=page )        # Click in TOC in left tab group
                meta.show( id='TOC',
                           file=file,
                           page=page,
                           page_count = page_count,
                        )
                select_pdf_tab()

            continue

        # ------------------------------------------------------------
        #   Click in browse music file tree

        #   'browse-music-file' event.
        #   aux[ key ] = { 'kind' : 'dir',
        #                  'path' : fullname,
        #                  'file' : '',
        #                  'children' : None  }

        # elif event == 'browse-music-files-DOUBLE-CLICK-':

        elif event == 'browse-music-files':
            index = values[ "browse-music-files" ]
            if index:
                parent_key = index[0]
                node = music_tree_aux[ parent_key ]

                # -----------------------------------------------------
                #   Click on folder that has not been populated yet

                pdf_extensions = [ '.pdf' ]         # Incoming ext converted to lower so don't need to enumerate them all here.

                if node['kind'] == 'dir' and node['children'] == None:
                    add_to_browse_tree( 'browse-music-files', music_tree, music_tree_aux, parent_key, node,
                                        fb.Music_File_Root, music_file_icon, pdf_extensions )

                # -----------------------------------------------------
                #   Click on leaf - show file.

                if node['kind'] == 'file':
                    fullpath = Path( fb.Music_File_Root, node['relpath'], node['file']  )
                    partialpath = Path( node['relpath'], node['file'] )

                    if verbose:
                        print( "Showing music: ", fullpath )

                    pdf.show_music_file( file=fullpath, page=1 )              # Click in Browse Music File Tree
                    meta.show(  id='Browse',
                                file=partialpath.as_posix(),
                                page=1,
                                page_count = pdf.get_info()[ 'page_count' ],   
                              )
                    toc.show( file=partialpath )
                    select_pdf_tab()

            continue

        # ----------------------------------------------------------------

        elif event == 'browse-audio-files':
            index = values[ "browse-audio-files" ]
            if index:
                parent_key = index[0]
                node = audio_tree_aux[ parent_key ]

                # -----------------------------------------------------
                #   Click on folder that has not been populated yet

                audio_extensions = conf.val('audio_file_extensions')

                if node['kind'] == 'dir' and node['children'] == None:
                    add_to_browse_tree( 'browse-audio-files', audio_tree, audio_tree_aux, parent_key, node,
                                        fb.Audio_File_Root, audio_file_icon, audio_extensions )

                # -----------------------------------------------------
                #   Click on leaf - show file.

                if node['kind'] == 'file':
                    fullpath = os.path.join( fb.Audio_File_Root, node['relpath'], node['file'] )

                    if verbose:
                        print( "Playing audio:", fullpath )

                    fb.play_audio_file( fullpath )
            continue

        # ----------------------------------------------------------------

        elif event == 'clear':
            window.Element( 'song-title' ).update( "" )
            window.Element( 'song-composer' ).update( "" )
          # window.Element( 'song-lyricist' ).update( "" )
            window.Element( 'song-artist' ).update( "" )
            window.Element( 'song-album' ).update( "" )
            window.Element( 'local-src' ).update( "" )
            window.Element( 'canonical' ).update( "" )
            continue

    # ----------------------------------------------------------------
    #   Break 'while True:' to here to end program. All cleanup already done.

# ---------------------------------------------------------------------------------------
#   main() is the entry point when packaged with PyInstaller or invoked as python -m birdland.
#       startup.py -> __main__.py

def main():
    do_main()

if __name__ == '__main__':
    t = Path( sys.argv[0] ).name           

    if t == 'birdland-build-tables':
        import build_tables
        build_tables.main()

    elif t == 'birdland-check-offsets':
        import check_offsets
        check_offsets.main()

    else:
        do_main()

# ---------------------------------------------------------------------------------------
