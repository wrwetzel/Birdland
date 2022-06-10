#!/usr/bin/python
# ---------------------------------------------------------------------------------------
#   birdland.py
# ---------------------------------------------------------------------------------------

import os
import sys
import platform
# import signal
# import subprocess
# import socket
import sqlite3
# import re
import json
import time
import copy
import datetime
# import importlib.metadata
from pathlib import Path
from collections import defaultdict
import configobj                 
import fitz
import click

import PySimpleGUI as sg
# import tkinter as tk
# import tk

import fb_utils
import fb_pdf
import fb_metadata
import fb_setlist
import fb_layout
import fb_index_pagelist
import fb_index_diff
import fb_local2canon_mgmt
import fb_canon2file_mgmt
import fb_config
import fb_make_desktop
import fb_menu_stats
import fb_search
import fb_index_create
import fb_version

# =======================================================================================
#   A few Constants

folder_icon =       'Icons/icons8-file-folder-16.png'
music_file_icon =   'Icons/Apps-Pdf-icon.png'
audio_file_icon =   'Icons/audio-x-generic-icon.png'
BL_Icon =           fb_utils.BL_Icon

# ---------------------------------------------------------------------------------------
#   A few globals.

music_tree = None
music_tree_aux = {}     # Metadata for music_tree

audio_tree = None
audio_tree_aux = {}     # Metadata for audio_tree

Select_Limit = None     # for pylint
MYSQL = SQLITE = FULLTEXT = None                
window = None
music_tree = None
music_tree_aux = None
audio_tree = None
audio_tree_aux = None

# ----------------------------------------
#   WRW 5 Mar 2022 - I want to localize status info in a class and add
#       a couple of indicators of audio and midi of title available.

class Status():
    def __init__( self, bar_element ):
        self.bar_element = bar_element
        self.pdf_count = 0
        self.pdf_len = 0
        self.audio_count = 0
        self.audio_len = 0
        self.music_count = 0
        self.music_len = 0
        self.midi_count = 0
        self.midi_len = 0
        self.chordpro_count = 0
        self.chordpro_len = 0
        self.jjazz_count = 0
        self.jjazz_len = 0
        self.youtube_count = 0
        self.youtube_len = 0
        self.current_audio = False
        self.current_midi = False
        self.current_jjazz = False
        self.current_chordpro = False

    def set_music_index( self, count, lenth ):
        self.pdf_count = count
        self.pdf_len = lenth

    def set_audio_index( self, count, lenth ):
        self.audio_count = count
        self.audio_len = lenth

    def set_music_files( self, count, lenth ):
        self.music_count = count
        self.music_len = lenth

    def set_midi_files( self, count, lenth ):
        self.midi_count = count
        self.midi_len = lenth

    def set_chordpro_files( self, count, lenth ):
        self.chordpro_count = count
        self.chordpro_len = lenth

    def set_jjazz_files( self, count, lenth ):
        self.jjazz_count = count
        self.jjazz_len = lenth

    def set_youtube_index( self, count, lenth ):
        self.youtube_count = count
        self.youtube_len = lenth

    def set_current_audio( self, val ):
        self.current_audio = val

    def set_current_midi( self, val ):
        self.current_midi = val

    def set_current_chordpro( self, val ):
        self.current_chordpro = val

    def set_current_jjazz( self, val ):
        self.current_jjazz = val

    def show( self ):
        # audio_avail = 'Audio' if self.current_audio else ''
        # midi_avail =  'Midi'  if self.current_midi else  ''
        audio_avail = '\U0001F50a' if self.current_audio else ''
        midi_avail =  '\U0001f39d '  if self.current_midi else  ''
        chordpro_avail =  'Cp '  if self.current_chordpro else  ''
        jjazz_avail =  'Jj '  if self.current_jjazz else  ''

        results =  "Search Results:   "
        results += f"Music Index: {self.pdf_len:>4} of {self.pdf_count:>4}      "
        results += f"Audio Index: {self.audio_len:>4} of {self.audio_count:>4}      "
        results += f"Music Files: {self.music_len:>4} of {self.music_count:>4}      "
        results += f"Midi Files: {self.midi_len:>4} of {self.midi_count:>4}      "
        results += f"Chordpro Index: {self.chordpro_len:>4} of {self.chordpro_count:>4}      "
        results += f"JJazz Index: {self.jjazz_len:>4} of {self.jjazz_count:>4}      "
        results += f"YouTube Index: {self.youtube_len:>4} of {self.youtube_count:>4}      "
        results += f"{audio_avail:>10}    {midi_avail:>10}   {chordpro_avail:>10}   {jjazz_avail:>10}"
    
        self.bar_element.update( results )

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

class Tabs_Control():
    def __init__( self ):                                                                                 
        self.idx_tabs = False
        self.c2f_tab = True

    def initialize( self ):
        self.idx_tabs = conf.val( 'show_index_mgmt_tabs' )
        self.c2f_tab = conf.val( 'show_canon2file_tab' )
        self.update( 'idx' )
        self.update( 'c2f' )

    def set( self, tab, val ):
        if tab == 'idx':
            self.idx_tabs = val
            self.update( 'idx' )
        elif tab == 'c2f':
            self.c2f_tab = val
            self.update( 'c2f' )

    def show( self, tab ):
        if tab == 'idx':
            self.idx_tabs = True
            self.update( 'idx' )
        elif tab == 'c2f':
            self.c2f_tab = True
            self.update( 'c2f' )

    def hide( self, tab ):
        if tab == 'idx':
            self.idx_tabs = False
            self.update( 'idx' )
        elif tab == 'c2f':
            self.c2f_tab = False
            self.update( 'c2f' )

    def toggle( self, tab ):
        if tab == 'idx':
            self.idx_tabs = not self.ids_tabs
          # self.idx_tabs = False if self.idx_tabs else True
            self.update( 'idx' )
        elif tab == 'c2f':
            self.c2f_tab = not self.c2f_tab 
          # self.c2f_tab = False if self.c2f_tab else True
            self.update( 'c2f' )

    def update( self, tab ):
        if tab == 'idx':
            window[ 'tab-mgmt-subtabs' ].update( visible = self.idx_tabs )
            # window[ 'tab-index-mgmt' ].update( visible = self.idx_tabs )
            # window[ 'tab-index-diff' ].update( visible = self.idx_tabs  )
            # window[ 'tab-local2canon-mgmt' ].update( visible = self.idx_tabs  )
        elif tab == 'c2f':
            window[ 'tab-canon2file-mgmt' ].update( visible = self.c2f_tab )

# ----------------------------------------
#   This is too small to put in a separate file
#   The Music_Viewer object represents the 'Music Viewer' tab.

# class Music_Viewer( fb_pdf.PDF ):
#     def __init__( self ):
#         super().__init__()

# ----------------------------------------
#   Extract a few paramaters from configuration and set in globals.
#   Must appear before call to it below.
#   WRW Late Mar 2022 - Replaced most globals with conf.val() or class.
#   Keep Select_Limit as global. Too many places to change.

def set_local_config():
    global Select_Limit
    Select_Limit = conf.val( 'select_limit' )

# --------------------------------------------------------------------------
#   Initialize classes in external modules. Note that classs are all global.
#       Sloppy? Don't know, but certainly convenient.
#   /// RESUME OK - Look into inheritance for this.

conf =      fb_config.Config()
fb =        fb_utils.FB()

#   /// RESUME - Cheating here by naming the Music_Viewer() object pdf. Fix it later as this
#       will be source of great confusion.

pdf =       fb_pdf.PDF()
# pdf =       Music_Viewer()

meta =      fb_metadata.Meta()
sl =        fb_setlist.Setlist()
pagelist =  fb_index_pagelist.PageList()
diff =      fb_index_diff.Diff()
l2c  =      fb_local2canon_mgmt.L2C()
c2f  =      fb_canon2file_mgmt.C2F()
create =    fb_index_create.Create()

#   And one local class

tabs_control = Tabs_Control()

# =======================================================================================
#   Call after run conf.do_configure()
#   Immediately update parameters with changed config.
#   Do this only when birdland fully launches, not on initial configuration window.

def do_configure_save_update():

    fb.set_class_config( )
    pdf.set_class_config( )
    sl.set_class_config( )
    pagelist.set_class_config( )
    l2c.set_class_config( )
    c2f.set_class_config( )
    set_local_config( )

    tabs_control.initialize()
    tabs_control.update( 'idx' )
    tabs_control.update( 'c2f' )

    # -------------------------------------------------------
    #   Not sure if want to hide entire PDF Viewer tab. Some metadata there might
    #       be useful even with external viewer. Yes, Definitely keep it.

    if conf.val( 'use_external_music_viewer' ):
        window['display-control-buttons' ].update( visible = False )
        window['display-control-buttons' ].hide_row()
    else:
        window['display-control-buttons' ].unhide_row()
        window['display-control-buttons' ].update( visible = True )

    # -------------------------------------------------------
    #   This doesn't change theme dynamically. Should it? No. Well documented in discussion that it does not.
    #   sg.theme( conf.val( 'theme' ) )

    # -------------------------------------------------------
    #   WRW 20 May 2022 - Update the browse trees. Relevant option values may have changed.

    global music_tree, audio_tree
    global music_tree_aux, audio_tree_aux

    music_tree = sg.TreeData()
    music_tree_aux = {}     # Metadata for music_tree
    initialize_browse_tree( 'browse-music-files', music_tree, music_tree_aux, fb.Music_File_Folders, fb.Music_File_Root )

    audio_tree = sg.TreeData()
    audio_tree_aux = {}     # Metadata for audio_tree
    initialize_browse_tree( 'browse-audio-files',  audio_tree, audio_tree_aux, fb.Audio_Folders, fb.Audio_File_Root )
    
# --------------------------------------------------------------
#   Find the last key + 1 in aux

def new_key( aux ):
    if aux.keys():
        return max( aux.keys() ) + 1
    return 1

# ------------------------------------------------

def nested_dict(n, dtype):
    if n == 1:
        return defaultdict(dtype)
    return defaultdict(lambda: nested_dict(n-1, dtype))

# ------------------------------------------------
#        tree.insert(parent,
#                    key,
#                    text,
#                    values,
#                    icon = None)

def initialize_browse_tree( tree_key, tree, aux, valid_folders, root_path ):

    if not root_path:
        return

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
#   Just for testing but keep.

def KEEP_do_profile( dc ):

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

#   WRW 5 June 2022 - changed window to lwindow for pylint

def initialize_gui( lwindow ):
    global music_tree, audio_tree
    global music_tree_aux, audio_tree_aux

    # -------------------------------------------------------
    #   Load Help file into PDF viewer for initial display.
    #   This needed to get graph size of Graph element established early for some reason.
    #   Must call previously call finalize() for this to work. That may have been only
    #   issue with initialization as size now OK without this.

    pdf.show_music_file( file=fb.get_docfile(), page=1, force=True )    # Initial display
    meta.show( id='Initial',
               mode='Ft',                # Text File
               file=fb.get_docfile(),
               page=1,
               page_count = 1,
               title='Bluebird Music Manager', )

    # size = lwindow.Element( 'display-graph-pdf' ).get_size()

    # -------------------------------------------------------
    #   Load initial data into music and audio browse trees (in left sidebar).

    music_tree = sg.TreeData()
    music_tree_aux = {}     # Metadata for audio_tree
    initialize_browse_tree( 'browse-music-files', music_tree, music_tree_aux, fb.Music_File_Folders, fb.Music_File_Root )
    
    audio_tree = sg.TreeData()
    audio_tree_aux = {}     # Metadata for audio_tree
    initialize_browse_tree( 'browse-audio-files',  audio_tree, audio_tree_aux, fb.Audio_Folders, fb.Audio_File_Root )
    
    # -------------------------------------------------------
    #   Set focus to title search box and select pdf display, which now contains help file.

    lwindow.Element( 'song-title' ).set_focus()
    lwindow.Element( 'tab-display-pdf' ).select()
    
    # -------------------------------------------------------
    #   Set saved values for setlist in both setlist Combo elements.
    
    current_name = sl.setlist_load()
    sl_names = sl.setlist_get_names()
    lwindow.Element(  'setlist-save-menu' ).update( values = sl_names, value=current_name )
    lwindow.Element(  'setlist-controls-menu' ).update( values = sl_names, value=current_name )
    
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
    
    # lwindow.bind( '<Configure>', 'Config-Event' )    # size of widget changed

    # --------------------------------------------
    #   Set the visibility of some tabs based on config options.
    #       Must do after get_config() and window created, can't do it at tabs_control.__init__().

    tabs_control.initialize()   

    # --------------------------------------------------------------------------
    #   Drop down to Tkinter to control the tabgroups. Need fill and expand for this not PSG expand_x, expand_y.
    #   This was an incredible pain to learn that fill is needed to get main tab bar to fill all available X space.
    #   The expand arg here overrides PySimpleGui expand_x and expand_y.
    #   See dummy exploration program "Play/expand-problem.py" for more details.
    
#/// RESUME   lwindow.Element( 'sidebar-tabgroup' ).Widget.pack( side = tk.LEFT, expand=False, fill=tk.Y )
#/// RESUME   lwindow.Element( 'main-tabgroup' ).Widget.pack( side = tk.LEFT, expand=True, fill=tk.BOTH )
    lwindow.Element( 'sidebar-tabgroup' ).Widget.pack( side = 'left', expand=False, fill='y' )
    lwindow.Element( 'main-tabgroup' ).Widget.pack( side = 'left', expand=True, fill='both')
    lwindow.set_alpha(1)     # Show window. It had been initialized with alpha of 0.
    
# --------------------------------------------------------------------------

def select_pdf_tab():
    if not conf.val( 'use_external_music_viewer' ):
        window.Element( 'tab-display-pdf' ).select()
        window.Element( 'display-graph-pdf' ).set_focus()

# --------------------------------------------------------------------------
#   Want more than can do in simple popup.
#   Show: Help->About Birdland
#   WRw 21 Mar 2022 - Pulled out into separate function to use with verbose, too.
#   WRW 30 May 2022 - Remove use of importlib. Only applicable when this installed by PyPi

def get_about_data():

    uname = os.uname()

    # try:
    #     version = importlib.metadata.version( 'birdland' )
    # except:
    #     try:
    #         version = importlib.metadata.version( 'birdland-wrwetzel' )
    #     except:
    #         version = 'not available'

    version = fb_version.Version

    # ----------------------------------
    if SQLITE:
        database = f"SqLite3, Database File: {Path( conf.home_confdir, conf.sqlite_database)}"

        if fb.get_fullword_available():
            fullword_notes = "Using fullwordmodule"
        else:
            fullword_notes = "Using LIKE"

        mysqldb_module_version = "Not applicable"


    if MYSQL:
        database = f"MySql, Database: '{conf.mysql_database}'"
        fullword_notes = ''

        import MySQLdb              # WRW 3 June 2022 - Imported in do_main() but not in namespace here.
        mysqldb_module_version = '.'.join([str(x) for x in MySQLdb.version_info ])

    # ----------------------------------
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        run_environment = "PyInstaller bundle"

    elif "__compiled__" in globals():
        run_environment = "Nuitka bundle"

    else:
        run_environment = "Python process"

    try:
        # timestamp = datetime.datetime.fromtimestamp( Path(sys.executable).stat().st_mtime ).strftime( '%a, %d-%b-%Y, %H:%M:%S')
        timestamp = datetime.datetime.fromtimestamp( Path(os.path.realpath(__file__)).stat().st_mtime ).strftime( '%a, %d-%b-%Y, %H:%M:%S')
    except Exception as e:
        # timestamp = f"not available for {sys.executable}"
        timestamp = f"not available for {os.path.realpath(__file__)}"

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
        MuPDF Library Version: {fitz.version[1]}
        PyMuPDF Module Version: {fitz.version[0]}
        ConfigObj Module Version: {configobj.__version__}
        MySQLdb Module Version: {mysqldb_module_version}

    Birdland:
        Version: {version}
        Run Environment: {run_environment}
        Package Type: {conf.Package_Type}
        birdland.py Timestamp: {timestamp}
        Database: {database}. {fullword_notes}

    Directories:
        Settings Directory: {conf.confdir}
        Program Directory: {conf.program_directory}
        Data Directory: {conf.data_directory}

    Executable Identity:
        Python executable: {sys.executable}
        Argv[0]: {sys.argv[0]}
        __file__: {__file__}
        Realpath( __file__ ): {os.path.realpath(__file__)}
    """
    return version, info_text

# --------------------------------------------------------------------------
#   WRW 12 May 2022 - Now that I have a contact form on the website let's direct
#       users there.

def do_contact():
    txt = """To contact us please go to:

    https://birdland.wrwetzel.com/contact.html

If writing about a problem please first copy the content from the

    Help->About

display and then paste it into the contact form.
"""
    conf.do_popup_raw( txt )

# --------------------------------------------------------------------------

def do_website():
    txt = """Birdland Website:

    https://birdland.wrwetzel.com/            
"""
    conf.do_popup_raw( txt )

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
            sg.Text( "Copyright \xa9 2022 Bill Wetzel", pad=((20,20),(8,0)), font=("Helvetica", 10, ), text_color='#e0e0ff' ),
        ],
        [
            sg.Text( "This software and index data is released under the terms of the MIT License.", pad=((20,20),(2,0)), font=("Helvetica", 10, ), text_color='#e0e0ff' ),
        ],
        [
            #   WRW 3 June 2022 - Volker got warning about 'None' not allowed in argument to size. Changed
            #       to fixed value of 80.

            sg.Multiline( info_text,
                    font=("Helvetica", 9 ),
                    pad=((20,20),(10,0)),
                  # size = ( None, info_text.count( '\n' ) +1 ),
                    size = ( 80, info_text.count( '\n' ) +1 ),                                               
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
    ]

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

        if event == 'config-button-cancel':     # WRW 5 June 2022 - elif -> if for pylint
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

  # logging = True if log else False
    logging = bool( log )

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
        do_show_recent_log()

    # -----------------------------------------------------------------------
    #   Set up some global variables defining which database and search type to use.

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
    fb_search.set_driver( MYSQL, SQLITE, False )

    conf.set_icon( BL_Icon )
    conf.set_classes( sg, fb )

    # ---------------------------------------------------------------
    #   Run birdland in the directory where the program lives for access
    #   to program modules, Icons and other related files. 

    #   Birdland running in conf.program_directory
    #   Data files are indicated by conf.data_directory

    #   WRW 10 Mar 2022 - A issue when running from PyInstaller packaged location with chdir here.
    #       cwd is fine when main() called from PyInstaller-packaged location.
    #       Change it only if called unbundled.
    #   /// RESUME OK - Think about this some more. 
    #   Perhaps set this up with script before calling birdland? No, OK as is.

    if conf.Package_Type in ('Installed', 'Unpacked'):          # WRW 5 June 2022 - changed from multiple ifs for pylint
        os.chdir( os.path.dirname(os.path.realpath(__file__)))

    #   if( conf.Package_Type == 'Development' or
    #      conf.Package_Type == 'GitHub' or
    #      conf.Package_Type == 'Tar' or
    #      conf.Package_Type == 'Setuptools'):
    #   
    #    os.chdir( os.path.dirname(os.path.realpath(__file__)))

    # conf.set_install_cwd( os.getcwd() )

    # -----------------------------------------------------------------------
    #   Some simple tests of configuration. First half can be done before get_config().

    announce = 0

    results, success = conf.check_home_config( confdir )
    if not success:
        if progress:
            print( "ERROR: Error in home configuration:", file=sys.stderr )
            print( '\n'.join( results ))
        conf.initialize_home_config( confdir )      # Need confdir to test if should have .birdland in home dir.
        announce += 1

    results, success = conf.check_specified_config( confdir )
    if not success:
        if progress:
            print( "ERROR: Error in specified configuration:", file=sys.stderr )
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
            print( "ERROR: Error in host-specific configuration:", file=sys.stderr )
            print( '\n'.join( results ))
        conf.initialize_hostname_config()
        announce += 1

    # -----------------------------------------------------------------------

    conf.set_class_variables()

    # -----------------------------------------------------------------------
    #   Need conf class set up early. Do others at same time.

    fb.set_classes( conf )
    pdf.set_classes( conf )
    meta.set_classes( conf, fb, pdf )
    sl.set_classes( conf, sg, fb, pdf, meta )
    pagelist.set_classes( conf, fb, pdf, meta, diff )
    diff.set_classes( conf, sg, fb, pdf, meta )
    create.set_classes( conf, sg, fb )                        
    l2c.set_classes( conf, fb, pdf, meta )
    c2f.set_classes( conf, fb, pdf, meta )
    fb_search.set_classes( conf, fb )

    # -----------------------------------------------------------------------
    #   Set up class-specific configuration options. Uses self.class.vals... in each class.

    fb.set_class_config()
    pdf.set_class_config( )
    sl.set_class_config( )
    pagelist.set_class_config( )
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
            print( "ERROR: Error in database configuration (birdland.py):", file=sys.stderr )
            print( '\n'.join( results ))

        if MYSQL:       # If check_database() failed for mysql it is likely because of user credentials.
            res = conf.get_user_and_password( confdir=confdir )

            if res:
                conf.initialize_database( database )        # Try after get DB credentials above.

            else:
                print( "ERROR: Can't continue without user credentials for MySql database", file=sys.stderr )
                sys.exit(1)

        if SQLITE:
            conf.initialize_database( database )

    # -----------------------------------------------------------------------

    global window
    # global music_tree
    # global music_tree_aux
    # global audio_tree
    # global audio_tree_aux

    # -----------------------------------------------------------------------
    #   Initialize these early in case joker clicks on blank line in table coming from initial values of "".
    #   Not an issue, now initialized without blank line.

    # indexed_music_file_table_data = audio_file_table_data = \
    #     midi_file_table_data = youtube_file_table_data = music_file_table_data = []

    # -----------------------------------------------------------------------
    #   Prepare connection to database.
    #   fb_utils needs dc before get_layout()

    have_db = False

    # -----------------------------------------------
    if MYSQL:
        try:
            import MySQLdb
            conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
          # c = conn.cursor()
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

    layout = fb_layout.get_layout( sg, fb, conf )     # Not a class yet so pass fb

    # ----------------------------------------------------
    #   Create the main window.
    #   WRW 23 Apr 2022 - set return_keyboard_events=False to suppress event on every keystroke. I don't
    #       think I was using that at all and annoying when printing events.
    #       No good, need it to get ScrollWheel events. All others are ignored.
    #       Looks like I'm back to using several keyboard event as they are non-specific to the element.

    window = sg.Window( fb_layout.Bluebird_Program_Title,
                        layout,                     # Layout now all in separate file.
                        return_keyboard_events=True,
                        resizable=True,
                        icon=BL_Icon,
                        alpha_channel = 0,          # To keep window invisible until size stable.
                     #  use_default_focus = False,  # To keep c2f button from getting focus. Set it explicitly as needed. Not working?
                        finalize=True,
                       )               

    # ----------------------------------
    #   Show pdf control buttons only for built-in viewer.

    if conf.val( 'use_external_music_viewer' ):
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
    #   /// RESUME OK - consider inheritance for this. Definitely. Someday. Not now.
    # ---------------------

    fb.set_window( window )

    # ---------------------

    pdf.set_window( window )
  # pdf.set_graph_element( window['display-graph-pdf'], window[ 'display-graph-slider' ] )
    pdf.set_graph_element( window['display-graph-pdf'] )
    pdf.register_page_change( 'pdf-hidden-page-change' )
    pdf.do_bind()
    pdf.set_for( "Music Viewer" )           # A little debugging help

    # ---------------------

    status_bar = Status( window['status-bar'] )

    meta.set_window( window )
    meta.set_elements(      # This allows the module to reference elements in the UI.
        window['display-page-title-exp'],
        window['display-page-local-exp'],
        window['display-page-canonical-exp'],
        window['display-page-file-exp'],
        window['display-page-number'],
        window['display-page-sheet'],
        window['current-audio-table'],
        window['current-midi-table'],
        window['table-of-contents-table'],
    )
    meta.set_dc( dc )
    meta.set_status( status_bar )
    meta.set_hacks( select_pdf_tab )

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

    pagelist.set_elements(      # This allows the module to reference elements in the UI.
        dc,
        window[ 'index-mgmt-table'          ],
        window[ 'index-mgmt-src-table'      ],
        window[ 'index-mgmt-local-table'    ],
        window[ 'index_mgmt_info_src'     ],
        window[ 'index_mgmt_info_local'     ],
        window[ 'index_mgmt_info_canonical'     ],
        window[ 'index_mgmt_info_file'     ],
        window[ 'tab-display-pdf'       ],
        window[ 'index_mgmt_info_page_count'       ],
    )

    pagelist.do_bind()

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

    create.set_elements(
        dc,
     #  window[ 'create-index-canonical' ],
        window[ 'create-index-title' ],
        window[ 'create-index-sheet' ],
        window[ 'create-index-page' ],
        window[ 'create-index-graph' ],
        window[ 'create-index-canonical-table' ],
        window[ 'create-index-main-frame' ],
        window[ 'create-index-review-table' ],
        window[ 'create-index-sheet-label' ],
    )
    create.set_icon( BL_Icon )
    create.do_bind()
    create.set_window( window )                                
    create.late_init()

    # ------------------------------------------------------------------------------------------------------

    l2c.set_elements(      # This allows the module to reference elements in the UI.
       dc,
       window['local2canonical-canonical-mgmt-table'],
       window['local2canonical-local-mgmt-table'],
       window['local2canonical-mgmt-src-combo'],
       window['canon-find-text-a'],
    )

    c2f.set_elements(      # This allows the module to reference elements in the UI.
       dc,
       window['canon2file-canonical-mgmt-table'],
       window['canon2file-link-mgmt-table'],
       window['canon-find-text-b'],
    )

    # --------------------------------------------------------------

    fb_search.set_elements( dc, Select_Limit, window, status_bar )

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

        # elif event == sg.WINDOW_CLOSED or event == 'Exit':
        elif event in (sg.WINDOW_CLOSED, 'Exit'):               # WRW 5 June 2022 - changed from if/or to in
            do_short_exit(0)

    if counter == limit:
        print( f"ERROR-DEV: Initial EVENT Loop did not recognize valid size of 'display-graph-pdf' after {limit * 10} ms.", file=sys.stderr )
        do_short_exit(1)

    # print( f"DEBUG: Time needed for 'display-graph-pdf' to settle: {counter*10} ms."  )

    # ----------------------------------------------------
    #   Once have valid size for 'display-graph-pdf' can initialize gui. Size needed
    #   in that to scale initial pdf to fit size of graph.
    #   Postpone announcement of no database credentials till here, after window up.

    initialize_gui( window )

    if record:
        recorder = Record( record )

    if playback:                              
        player = Record( playback )
        player.load()

    # ========================================================================
    #   *** Main EVENT Loop ***
    #   WRW 7 Mar 2022 - added rudimentary record/play function for testing.

    while True:
        if playback:
            event, values, last_sleep = player.get()
            _, _ = window.Read( timeout = last_sleep * 1000 )

        else:
            event, values = window.Read()           # *** Normal case.

            if record:
                recorder.rec( event, values )

        # print( "/// main:", event )

        main_tab = window[ 'main-tabgroup' ].get()
        sub_tab = window[ 'index-mgmt-tabgroup' ].get()
        sidebar_tab = window[ 'sidebar-tabgroup' ].get()

        # print( "*** main:", main_tab, "sub:", sub_tab )

        # ------------------------------------------------------------------
        #   WRW - 15 Jan 2022 - Try moving this to the top. Working on error messages
        #       when close with 'X' button in window title. Yup, solved problem.
        #       NG when below "if '::' in event:". Must be above logging and verbose
        #       since event is None.

        # if event == sg.WINDOW_CLOSED or event == 'Exit':
        if event in (sg.WINDOW_CLOSED, 'Exit'):      # WRW 5 June 2022 - changed from if/or to in
            do_full_exit(0)

        # ------------------------------------------------------------------

        if logging:
            if event not in [ 'MouseWheel:Down', 'MouseWheel:Up' ]:
                fb.log( event, values[ event ] if event in values else "-")
            fb.log_histo( event, values[ event ] if event in values else "-" )

        # fb.log( 'indexed_music_file_table_data',  len( indexed_music_file_table_data ) )
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

                if menu_event == 'menu-contact':
                    do_contact()
                    continue

                if menu_event == 'menu-website':
                    do_website()
                    continue

                elif menu_event == 'menu-tutorial':
                    pdf.show_music_file( file=fb.get_docfile(), page=1, force=True )        # Help in menu
                    meta.show( id='Help',
                               mode='Ft',                # Text File
                               file=fb.get_docfile(),
                               page=1,
                               page_count = 1,
                               title='Bluebird Music Manager', )

                    select_pdf_tab()
                    continue

                elif menu_event == 'menu-configure':
                    saved = conf.do_configure()
                    if saved:
                        do_configure_save_update()
                    continue

                # ------------------------------------------------------------------
                #   WRW 30 Mar 2022 - A little different.

                # elif menu_event == 'menu-stats':

                elif menu_event.startswith( 'menu-stats' ):
                    t = menu_event.removeprefix( 'menu-stats-' )
                    fb_menu_stats.do_menu_stats( t, window, dc, fb )
                    continue

                # ------------------------------------------------------------------
                #   WRW 29 May 2022 - After a lot of time invested in support for the self-contained packages I
                #       decided not to use them for now and probably for ever. They are huge and no real benefit
                #       other than simplicity. Back off from that now. Now execute the build_tables.py command
                #       that is definitely here rather than bl-build-tables linked to above that may not be
                #       in .local/bin if the install command is not run and are executed from the cloned or
                #       unzipped directory, a possibility for some users. The birdland, 
                #       bl-build-tables, and bl-diff-index links are for convenience so don't have to expose
                #       the *py file names and include 'bl-' in name to reduce likelihood of conflict.

                elif menu_event == 'menu-rebuild-all':
                    # fb.run_external_command( [ 'bl-build-tables', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './build_tables.py', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-source-priority':
                    # fb.run_external_command( [ 'bl-build-tables', '--src_priority', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './build_tables.py', '--src_priority', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-audio':
                    txt = """\nScanning your audio library may take a long time depending on size of your library.\n
                            Do you really want to do this?
                          """
                    t = conf.do_popup_ok_cancel( txt )
                    if t == 'OK':
                        # fb.run_external_command( [ 'bl-build-tables', '--scan_audio', '--audio_files', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                        fb.run_external_command( [ './build_tables.py', '--scan_audio', '--audio_files', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-page-offset':
                    # fb.run_external_command( [ 'bl-build-tables', '--offset', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './build_tables.py', '--offset', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-rebuild-canon2file':
                    # fb.run_external_command( [ 'bl-build-tables', '--canon2file', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './build_tables.py', '--canon2file', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-convert-raw-sources':
                    # fb.run_external_command( [ 'bl-build-tables', '--convert_raw', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './build_tables.py', '--convert_raw', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                # elif menu_event == 'menu-test-db-times':
                #     do_menu_test_db_times()
                #     continue

                # --------------------------------------------------

                elif menu_event == 'menu-summary':
                    # fb.run_external_command( [ 'bl-diff-index', '--summary', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './diff_index.py', '--summary', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-page-summary':
                    # fb.run_external_command( [ 'bl-diff-index', '--page_summary', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './diff_index.py', '--page_summary', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

                elif menu_event == 'menu-verbose':
                    # fb.run_external_command( [ 'bl-diff-index', '--verbose', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    fb.run_external_command( [ './diff_index.py', '--verbose', '--all', '-c', conf.confdir.as_posix(), '-d', fb.get_driver() ] )
                    continue

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
                    tabs_control.toggle( 'idx' )

                elif menu_event == 'menu-canon2file-tab':
                    tabs_control.toggle( 'c2f' )

                continue    # Menu item not recognized
            continue        # len != 2

        # END of if '::' in event:
        # ----------------------------------------------------------------
        #   Process events is the external classes.
        #   process_events() returns True if it procssed one, else False.
        #   This must be below '::' processing above.
        #   WRW 26 Apr 2022 - Make processing tab-specific.

        #   Summary of tab names. A * indicates tab-specific processing below
        #       All else is common to all tabs including sub-tabs.

        #       * tab-setlist-table
        #       * tab-display-pdf
        #       * tab-canon2file-mgmt
        #       tab-indexed-music-file-table
        #       tab-audio-file-table
        #       tab-music-filename-table
        #       tab-midi-file-table
        #       tab-youtube-table

        #       * tab-mgmt-subtabs tab-index-compare
        #       * tab-mgmt-subtabs tab-index-page-list
        #       * tab-mgmt-subtabs tab-create-index
        #       * tab-mgmt-subtabs tab-local2canon-mgmt

        # ----------------------

        #   WRW 5 June 2022 - add 'event ==' before 'display-button-add-to-setlist' 

        elif( main_tab == 'tab-setlist-table' or event == 'display-button-add-to-setlist' ) and sl.process_events( event, values ):
            continue

        # Note processing events for pdf and meta for tab-display-pdf

        elif main_tab == 'tab-display-pdf' and pdf.process_events( event, values ):         
            continue

        elif main_tab == 'tab-display-pdf' and meta.process_events( event, values ):
            continue

        #   WRW 15 May 2022 - Click in TOC. TOC is processed in fb_metadata.py.

        elif sidebar_tab == 'tab-table-of-contents' and meta.process_events( event, values ):
            continue

        elif main_tab == 'tab-canon2file-mgmt' and c2f.process_events( event, values ):
            continue

        # ----------------------

        elif main_tab == 'tab-mgmt-subtabs' and sub_tab == 'tab-index-compare' and diff.process_events( event, values ):
            continue

        elif main_tab == 'tab-mgmt-subtabs' and sub_tab == 'tab-index-page-list' and  pagelist.process_events( event, values ):
            continue

        elif main_tab == 'tab-mgmt-subtabs' and sub_tab == 'tab-create-index' and create.process_events( event, values ):
            continue

        elif main_tab == 'tab-mgmt-subtabs' and sub_tab =='tab-local2canon-mgmt' and l2c.process_events( event, values ):
            continue

        # ----------------------
            
        elif fb_search.process_events( event, values ):
            ( indexed_music_file_table_data,
                audio_file_table_data,
                music_file_table_data,
                midi_file_table_data,
                chordpro_file_table_data,
                jjazz_file_table_data,
                youtube_file_table_data ) = fb_search.get_search_results()
            continue

        # ------------------------------------------------------------------
        #   WRW 3 Mar 2022 - defer loading index management and related tables until tab activated.
        #   This prevents extraneous error messages on first launch before fully configured.
        #   User will only get error if screws around and clicks the tab before configuring.

        elif event == 'main-tabgroup':
            tab = values[ 'main-tabgroup' ]

            if tab == 'tab-canon2file-mgmt':
                window[ 'c2f-help' ].set_focus()        # This takes focus away from first element, a button.
                c2f.load_tables()                       #    and sets it to a text message where it is benign.

            elif tab == 'tab-mgmt-subtabs':
              # pagelist.load_tables()                      # Load first tab when index management subtabs selected.
                diff.load_tables()                      # Change this when change order of index-management sub-tabs.

            continue

        # ------------------------------------------
        #   Index Management sub-tab clicked

        elif event == 'index-mgmt-tabgroup':
            tab = values[ 'index-mgmt-tabgroup' ]

            if tab == 'tab-local2canon-mgmt':
                l2c.load_tables()
                continue

            elif tab == 'tab-index-page-list':
                pagelist.load_tables()
                continue

            elif tab == 'tab-index-diff':
                diff.load_tables()
                continue

            elif tab == 'tab-create-index':
                create.load_tables()
                continue

        # ------------------------------------------------------------------
        #   WRW 29 Apr 2022 - Trigger a metadata update when browse-src-combo changes

        elif event == 'browse-src-combo':
            pdf.report_page_change()

        # ------------------------------------------------------------------

        elif event == 'stop-audio-youtube':
            fb.stop_audio_file()
            fb.close_youtube_file()
            continue

        # ----------------------------------------------------------------

        elif event == 'close-music':
            pdf.close_ext()
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
            if indexed_music_file_table_data:

                if "indexed-music-file-table" in values and len( values[ "indexed-music-file-table" ] ):
                    index = values[ "indexed-music-file-table" ][0]

                    title =     indexed_music_file_table_data[ index ][0]
                    canonical = indexed_music_file_table_data[ index ][2]
                    page =      indexed_music_file_table_data[ index ][3]
                    sheet =     indexed_music_file_table_data[ index ][4]
                    src   =     indexed_music_file_table_data[ index ][5]
                    local =     indexed_music_file_table_data[ index ][6]
                    file  =     indexed_music_file_table_data[ index ][7]

                    if not file:
                        sg.popup( f"\nNo music file available for:\n\n   '{title}'\n\n    Canonical: {canonical}\n",
                            title='Birdland Warning',
                            icon=BL_Icon,
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
                                       mode='Fi',                # Music File with Index data
                                       file=file,
                                       title=title,
                                       canonical=canonical,
                                       sheet=sheet, 
                                       src=src,
                                       local=local, 
                                       page=page,
                                       page_count = pdf.get_info()[ 'page_count' ],
                                     )

                            select_pdf_tab()

                else:
                    do_error_announce( "ERROR: Unexpected values content for 'indexed-music-file-table' event", values[ event ] )
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
                    meta.show( id='FileTable',
                               mode='Fp',                # Music File, possible, index data
                               file=relpath.as_posix(),
                               page=1,
                               page_count = pdf.get_info()[ 'page_count' ],   
                             )
                    select_pdf_tab()

                else:
                    do_error_announce( "ERROR: Unexpected values content for 'music-filename-table' event", values[event] )
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
                    do_error_announce( "ERROR: Unexpected values content for 'audio-file-table' event", values[event] )
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
                    do_error_announce( "ERROR: Unexpected values content for 'audio-file-table' event", values[event] )
            continue

        # ----------------------------------------------------------------
        #   WRW 27 Apr 2022
        #   Handling show_chordpro_file() a little differently than other show_*_file() routines.

        elif event == 'current-chordpro-table':
            if chordpro_file_table_data:
                if "current-chordpro-table" in values and len( values[ "current-chordpro-table" ] ):

                    index = values[ "current-chordpro-table" ][0]
                    title = chordpro_file_table_data[ index ][0]
                 #  artist = chordpro_file_table_data[ index ][1]
                    file = chordpro_file_table_data[ index ][2]
                    fullpath = Path( conf.val( 'chordpro_file_root' ), file )

                    def show_chordpro_file_callback( tfile ):
                      # pdf.show_music_file( file=tfile, page=1, force=True )
                        pdf.show_music_file( file=tfile, page=1 )           # let show_music_file use external if user wants it.
                        meta.show( id='ChordPro',                           # Clear out any residual data.
                            mode='Ft',
                            file=file,
                            page=1,
                            page_count = pdf.get_info()[ 'page_count' ],
                            title=title
                        )

                        select_pdf_tab()

                    if not fullpath.is_file():
                        conf.do_nastygram( 'chordpro_file_root', fullpath )
                        continue

                    fb.show_chordpro_file( fullpath, show_chordpro_file_callback )

                else:
                    do_error_announce( "ERROR: Unexpected values content for 'current-chordpro-table' event", values[event] )
            continue

        # ----------------------------------------------------------------
        #   WRW 27 Apr 2022

        elif event == 'current-jjazz-table':
            if jjazz_file_table_data:

                if "current-jjazz-table" in values and len( values[ "current-jjazz-table" ] ):
                    index = values[ "current-jjazz-table" ][0]
                    title = jjazz_file_table_data[ index ][0]
                    file = jjazz_file_table_data[ index ][1]
                    fullpath = Path( conf.val( 'jjazz_file_root' ), file )

                    if not fullpath.is_file():
                        conf.do_nastygram( 'jjazz_file_root', fullpath )
                        continue

                    fb.show_jjazz_file( fullpath )

                else:
                    do_error_announce( "ERROR: Unexpected values content for 'current-jjazz-table' event", values[event] )
            continue

        # ----------------------------------------------------------------

        elif event == 'current-audio-table':
            if "current-audio-table" in values and len( values[ "current-audio-table" ] ):
                index = values[ "current-audio-table" ][0]

                table_data = window['current-audio-table'].get()    # Returns 2d array

                file = table_data[ index ][2]
                path = os.path.join( fb.Audio_File_Root, file )
                fb.play_audio_file( path )

            else:
                do_error_announce( "ERROR: Unexpected values content for 'current-audio-table' event", values[event] )

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
                do_error_announce( "ERROR: Unexpected values content for 'current-midi-table' event", values[event] )

            continue

        # ----------------------------------------------------------------
        #   Click in YouTube file table
        #       headings = [ "Title", "YT Title", "Duration", "yt_id" ],

        elif event == 'youtube-file-table':
            if youtube_file_table_data:
                if "youtube-file-table" in values and len( values[ "youtube-file-table" ] ):
                    index = values[ "youtube-file-table" ][0]

                  # ytitle = youtube_file_table_data[ index ][1]
                    yt_id = youtube_file_table_data[ index ][3]

                    # fb.open_youtube_file( ytitle )
                    fb.open_youtube_file_alt( yt_id )

                else:
                    do_error_announce( "ERROR: Unexpected values content for 'youtube-file-table' event", values[event] )
            continue

        # ----------------------------------------------------------------
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
                # Incoming extension converted to lower so don't need to enumerate them all here.

                pdf_extensions = [ '.pdf' ]         

                if node['kind'] == 'dir' and node['children'] is None:
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
                    page_count = pdf.get_info()[ 'page_count' ]

                    select_pdf_tab()

                    # --------------------------------------------
                    #   WRW 28 Apr 2022 - Populate 'browse-src-combo' with srcs for selected book, if any.
                    #   Add a little info for selected book.

                    canonical = fb.get_canonical_from_file( partialpath.as_posix() )
                    if canonical:
                        srcs = fb.get_srcs_by_canonical( canonical )
                        canon_info = canonical
                        if srcs:
                            window[ 'browse-src-combo' ].update( values = srcs, set_to_index = 0 )      # First is highest priority
                            src_info = f"File indexed by: {', '.join( srcs )}"
                        else:
                            window[ 'browse-src-combo' ].update( values = [] )
                            src_info = "File not indexed"

                    else:
                        canon_info = "File not mapped to canonical"
                        src_info = "File not indexed"
                        window[ 'browse-src-combo' ].update( values = [] )
                        srcs = []

                  # info_txt = f"{Path(partialpath).name}\nPages: {page_count}\n{canon_info}\n{src_info}"
                    info_txt = f"{Path(partialpath).name}\n{canon_info}\n{src_info}"
                    window[ 'browse-book-info' ].update( info_txt )

                    meta.show(  id='Browse',                # After update 'browse-src-combo', using value below
                                mode='Fs',                  # Music file, possibly src specified
                                file=partialpath.as_posix(),
                                page=1,
                                page_count = page_count,
                              # src_from_combo = values[ 'browse-src-combo' ],      # No good, not available yet.
                                src_from_combo = srcs[0] if srcs else None          # Use first, highest priority src.
                              )
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

                if node['kind'] == 'dir' and node['children'] is None:
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
    do_main()

# ---------------------------------------------------------------------------------------

if False and __name__ == '__main__':
    t = Path( sys.argv[0] ).name           

    if t == 'bl-build-tables':
        import build_tables
        build_tables.main()

    elif t == 'bl-diff-index':
        import diff_index
        diff_index.main()

    else:
        do_main()

# ---------------------------------------------------------------------------------------
