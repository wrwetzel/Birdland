#!/usr/bin/python
# ---------------------------------------------------------------------------------------
#   fb_metadata.py

#   WRW 21 Jan 2022 - module for displaying music file metadata in the
#       PDF display window.

#   WRW 29 Apr 2022 - As I approach the completion of the development of Birdland I bumped into
#       still some confusion regarding the source and display of metadata. 
#       The problem was I was thinking that show() should make the best of whatever parameters it is
#       called with and show whatever data possible. In reality it is called with only a small
#       number of arg profiles.

#       In the hope of simplifying this I added a 'mode' parameter, which identifies the
#       set of arg profile and reduces the number of paths through the code.

#       Primary calls to this are only from birdland.py 
#       A secondary call is also from fb_setlist.py but that is with data from a primary call.
#       Additional calls in fb_index_pagelist.py and fb_index_diff.py are 'if False:' removed.

#       'mode':
#           'Ft' - Text / Chordpro file, index data not meaningful.                         
#           'Fi' - Music File with index data.
#           'Fp' - Music File, possibility of inferring index data.
#           'Fs' - Music File, src may be explicitly given in browse combo box.
#           'N'  - Bug catacher on code removed by 'if False:'

#       Inferring index data:
#           Music File -> none                          Canonical to File not mapped

#           Music File -> Canonical -> none             Local to Canonical not mapped

#           Music File -> Canonical -> local/src        One to many relationship that must
#                                   -> ...              be resolved by src_priority, imperfect.
#                                   -> local/src

#           Music File -> Canonical -> local/src        Src give explicitly by browse combo

#       Note that browse combo can change while viewing one book and must be checked on every
#           page change.

#       Note also that this approach will include some redundant code but it will
#           be simpler and offer more peace-of-mind. At first blush it looks great, much simpler.

#       Metadata here is infomation related to the current book and page including
#           page, sheet, title(s), src, local, canonical, the table of contents, and
#           the current audio and midi tables (i.e. audio/midi files matching current title)

#       Redo table of contents logic: built toc from metadata.show(), move toc Click processing to here,
#           remove toc entirely from birdland.py.

# --------------------------------------------------------------
#       In all cases populate these metadata gui elements with either constructive data or blanks.
#           src included in local_ele string. Let's try clearing them all and populating only as
#           have data, not clearing only of don't have data.

#           self.title_ele        
#           self.local_ele         
#           self.canonical_ele             
#           self.file_ele       
#           self.number_ele          
#           self.sheet_ele         

#           self.current_audio_ele          # Sidebar, audio files matching title
#           self.current_midi_ele           # Sidebar, midi files matching title

# ---------------------------------------------------------------------------------------

def make_boolean( val ):
    parts = val.split()
    t = [ '+' + x for x in parts ]
    val = " ".join( t )
    return val

class Meta():

    # --------------------------------------------------------------
    def __init__( self ):
        self.src = None
        self.local = None
        pass

    def set_elements( self, title, local, canonical, file, number, sheet, 
                      current_audio, current_midi, table_of_contents ):
        self.title_ele = title
        self.local_ele  = local
        self.canonical_ele  = canonical
        self.file_ele  = file
        self.number_ele  = number
        self.sheet_ele  = sheet
        self.current_audio_ele = current_audio
        self.current_midi_ele = current_midi
        self.table_of_contents_ele = table_of_contents

    def clear_elements( self ):         # file current_audio and current_midi always set or cleared explicitly
        self.title_ele.update( value = '' )
        self.local_ele.update( value = '' )
        self.canonical_ele.update( value = '' )
        self.number_ele.update( value = '' )
        self.sheet_ele.update( value = '' )
        self.update_current_audio( [] )         # Content in left-sidebar for audio and midi matching title
        self.update_current_midi( [] )          
        self.table_of_contents_ele.update( values = [] )
        self.table_of_contents_data = []

    def set_classes( self, conf, fb, pdf ):
        self.conf = conf
        self.fb = fb
        self.pdf = pdf

    def set_status( self, status ):
        self.status = status                                                                      

    def set_dc( self, dc ):
        self.dc = dc

    def set_driver( self, t1, t2, t3 ):
        global MYSQL, SQLITE, FULLTEXT
        MYSQL = t1
        SQLITE = t2
        FULLTEXT = t3

    def set_window( self, window ):
        self.window = window

    def set_hacks( self, select_pdf_tab ):
        self.select_pdf_tab = select_pdf_tab

    # --------------------------------------------------------------

    def proc_sheet( self, sheet, src, local ):
        if sheet:
            self.sheet_ele.update( value = f"Sheet/Title #: {sheet}" )
            titles_array = self.fb.get_titles_from_sheet( sheet, src, local )
            titles_text = '\n\n'.join( titles_array )
            self.title_ele.update( value = titles_text )
            self.update_current_audio( titles_array )
            self.update_current_midi( titles_array )
            self.info[ 'titles' ] = titles_array
            self.info[ 'sheet'  ] = sheet

        else:
            self.sheet_ele.update( value = f"Sheet: - " )

    # --------------------------------------------------------------

    def process_events( self, event, values ):

        # ------------------------------------------------------------------
        #   User changed PDF page with icons, keystrokes, or scrolling
        #   Don't do anything if don't have database yet.

        if event == 'pdf-hidden-page-change':
            p = self.pdf.get_info()
            self.show_page_update(
                page = p[ 'page' ],
                page_count = p[ 'page_count' ],
                src_from_combo = values[ 'browse-src-combo' ]
            )

            return False        # Others may want this event, too

        # ------------------------------------------------------------------
        #   table_of_contents_data: [ [ row[ 'title' ], row[ 'sheet' ] ]

        elif event == 'table-of-contents-table':
            if 'table-of-contents-table' in values and len( values[ "table-of-contents-table" ] ):
                index = values[ "table-of-contents-table" ][0]
                sheet = self.table_of_contents_data[ index ][1]

                if sheet:
                    src = self.info[ 'src' ]            # Saved by show()
                    local = self.info[ 'local' ]

                    page = self.fb.get_page_from_sheet( sheet, src, local )
                    if page:
                        self.pdf.goto_page( int( page ) )
                        self.select_pdf_tab()               # WRW 15 May 2022

            return True

        # ------------------------------------------------------------------
        return False

    # --------------------------------------------------------------
    #   Populate the supplied or found metadata info in PDF window and save a copy.
    #   Called after pdf.show_music_file() with all available parameters.
    #   Fill in missing if possible.
    #   Always have 'file', page, and page_count
    #   WRW 29 Apr 2022 - added 'mode'.

    def show( self, id=None, mode=None, file=None, page=None, sheet=None, src=None, local=None,
                    canonical=None, page_count=None, title=None, src_from_combo = None):

        # print( f"Show: '{id}', '{mode}', '{file}', '{page}', '{sheet}', '{src}', '{local}', '{canonical}', '{page_count}', '{title}', '{src_from_combo}'" )

        titles_array = []
        self.clear_elements()

        # ---------------------------------------------------------------------------------

        self.info = {               # Save data from most recent call, need some for setlist, may need more later.
            'id' :          id,     # Initially used only for debugging but on 28 Apr 2022 it looks useful
            'mode' :        mode,
            'file' :        file,
            'page' :        page,
            'sheet' :       sheet,
            'src' :         src,
            'local' :       local,
            'canonical' :   canonical,
            'title' :       title,          # /// RESUME Is this used anywhere?
            'titles' :      [],
            'page_count' :  page_count,
        }

        # print( "/// Show() Info:", self.info )

        # ----------------------------------------------------------------------
        #   Bug catcher. Mode must be given and must not be 'N'

        if not mode or mode not in [ 'Ft', 'Fi', 'Fp', 'Fs' ]:
            print( f"ERROR-DEV: Unexpected value of 'mode': {mode}", file=sys.stderr )
            sys.exit(1)

        # ----------------------------------------------------------------------
        #   *** File ***

        #   WRW 22 Jan 2022 - file is now partial path, i.e., without root to files.
        #   If no file given don't clear display, keep old value.
        #   File now always given, removed test for it.

        if '/' in file:
            files = file.split('/')
            file1 = '/'.join( files[ 0:-1] ) + '/'
            file2 = files[ -1]

        else:
            file1 = file
            file2 = ''

        self.file_ele.update( value = f'{file1}\n{file2}' )

        # ----------------------------------------------------------------------
        #   *** Page ***

        if page and page_count:
            self.number_ele.update( value = f"Page: {page} of {page_count}" )

        # ----------------------------------------------------------------------
        #           'Ft' - Text / Chordpro file, index data not meaningful.
        #           'Fi' - Music File with index data.
        #           'Fp' - Music File, possibility of inferring index data.
        #           'Fs' - Music File, src may be explicitly given in browse combo box.
        # ----------------------------------------------------------------------

        if mode == 'Ft':
            if title:
                self.title_ele.update( value = title )

        # ----------------------------------------------------------------------
        # Have index data in calling args, i.e. click in Music Index

        elif mode == 'Fi':
            self.canonical_ele.update( value = canonical )
            self.local_ele.update( value = f"{local} - {src}" )
            self.proc_sheet( sheet, src, local )
            self.table_of_contents_data = self.fb.get_table_of_contents( src, local )
            self.table_of_contents_ele.update( values = self.table_of_contents_data  )

        # ----------------------------------------------------------------------
        #   May have src explicitly given in browse combo box. 
        #   Backtrack to get index data, if any from that.

        elif mode == 'Fs':
            canonical = self.fb.get_canonical_from_file( file )
            if canonical:
                self.canonical_ele.update( value = canonical )
                self.info[ 'canonical' ] = canonical
                src = src_from_combo
                if src:
                    local = self.fb.get_local_from_src_canonical( src, canonical )
                    if local:
                        self.info[ 'src' ] = src
                        self.info[ 'local' ] = local
                        self.local_ele.update( value = f"{local} - {src}" )                                                  
                        sheet = self.fb.get_sheet_from_page( page, src, local )
                        self.proc_sheet( sheet, src, local )
                        self.table_of_contents_data = self.fb.get_table_of_contents( src, local )
                        self.table_of_contents_ele.update( values = self.table_of_contents_data  )

        # ----------------------------------------------------------------------
        #   May possibly be able to recover index data by backtracking and with src_priority

        elif mode == 'Fp':
            canonical = self.fb.get_canonical_from_file( file )
            if canonical:
                rows = self.fb.get_src_local_from_canonical( canonical )
                src, local = rows[0]         # Returns src/local list ordered by src_priority. Select highest priority.
                if src and local:
                    self.info[ 'src' ] = src
                    self.info[ 'local' ] = local
                    self.local_ele.update( value = f"* {local} - {src}" )     # * signifies estimate, i.e., src by priority

                    sheet = self.fb.get_sheet_from_page( page, src, local )
                    self.proc_sheet( sheet, src, local )
                    self.table_of_contents_data = self.fb.get_table_of_contents( src, local )
                    self.table_of_contents_ele.update( values = self.table_of_contents_data  )

    # ---------------------------------------------------------------------------------------
    #   WRW 24 Jan 2022 - New page in existing document. User can change browse_src_combo 
    #       while looking at book. Get value for every page if browsing.
    #   WRW 29 Apr 2022 - Redo using explicit approach.

    def show_page_update( self, page, page_count, src_from_combo ):

        self.info[ 'titles' ] = []                  # Clear all first, may populate below.
        self.title_ele.update( value = '' )
        self.local_ele.update( value = '' )
        self.sheet_ele.update( value = '' )
        self.update_current_audio( [] )
        self.update_current_midi( [] )

        # ---------------------------------------------------

        self.number_ele.update( value = f"Page: {page} of {page_count}" )
        self.info[ 'page' ] = page

        # ---------------------------------------------------
        #   First try to get current src if in 'Fs' mode.

        ok = False
        if self.info[ 'mode' ] == 'Fs':
            src = src_from_combo 
            if src:
                local = self.fb.get_local_from_src_canonical( src, self.info[ 'canonical' ] )
                if local:                             # Success getting local from src/canonical
                    ok = True

        if not ok:                          # Otherwise, use src/local saved in show() above.
            src = self.info[ 'src' ]
            local = self.info[ 'local' ]

        # ---------------------------------------------------
        #   Only meaningful to deal with sheet if have src and local

        if src and local:
            self.info[ 'src' ] = src            # Save values possibly changed in 'Fs' mode.
            self.info[ 'local' ] = local
            self.local_ele.update( value = f"{'*' if self.info[ 'mode' ] == 'Fp' else ''} {local} - {src}" )     # * signifies estimate, i.e., src by priority

            sheet = self.fb.get_sheet_from_page( int(page), src, local )
            # print( "///", sheet, page, src, local )
            self.proc_sheet( sheet, src, local )

    # ---------------------------------------------------------------------------------------
    #   The metadata object stores information for saving to setlist.

    def get_info( self ):
        return self.info

    # ---------------------------------------------------------------------------------------
    #   WRW 29 Jan 2022 - New idea - show audio files matching current titles

    def update_current_audio( self, titles_a ):
        table = []
        for current_title in titles_a:
            for title, artist, file in self.get_audio_from_titles( current_title ):
                table.append( (title, artist, file ) )

        self.fb.safe_update( self.current_audio_ele, table, None )

        if table:
            self.status.set_current_audio( True )
        else:
            self.status.set_current_audio( False )

        self.status.show()

    # -------------------------------

    def update_current_midi( self, titles_a ):
        table = []
        for current_title in titles_a:
            for rpath, file in self.get_midi_from_titles( current_title ):
                table.append( (rpath, file ) )

        self.fb.safe_update( self.current_midi_ele, table, None )

        if table:
            self.status.set_current_midi( True )
        else:
            self.status.set_current_midi( False )

        self.status.show()


    # -------------------------------

    def get_audio_from_titles( self, title ):
        if MYSQL:
            query = f"""
                SELECT title, artist, file
                FROM audio_files
                WHERE title = %s
            """

        if SQLITE:
            query = f"""
                SELECT title, artist, file
                FROM audio_files
                WHERE title = ?
            """

        data = (title,)
        self.dc.execute( query, data )
        rows = self.dc.fetchall()

        res = [ [row[ 'title' ], row[ 'artist' ], row[ 'file' ] ] for row in rows ] if rows else []

        return res

    # -------------------------------

    def get_midi_from_titles( self, title ):
        data = []
        if MYSQL:
            title = make_boolean( title )
            query = f"""
                SELECT rpath, file
                FROM midi_files
                WHERE MATCH( file ) AGAINST ( %s IN BOOLEAN MODE )
                ORDER BY file
            """
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT rpath, file
                    FROM midi_files_fts
                    WHERE file MATCH ?
                    ORDER BY rank
                """
                data.append( title )

            else:
                w, d = self.fb.get_fulltext( "file", title )
                query = f"""
                    SELECT rpath, file
                    FROM midi_files    
                    WHERE {w}
                    ORDER BY file
                """
                data.extend( d )

        # parts = title.split()
        # t = [ f'+{x}' for x in parts if len(x) >= 4]
        # title = " ".join( t )

        # print( query )
        # print( data )

        self.dc.execute( query, data )
        rows = self.dc.fetchall()

        res = [ [row[ 'rpath'], row[ 'file' ]] for row in rows ] if rows else []

        return res

# ---------------------------------------------------------------------------------------
