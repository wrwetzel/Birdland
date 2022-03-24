#!/usr/bin/python
# ---------------------------------------------------------------------------------------
#   fb_metadata.py

#   WRW 21 Jan 2022 - module for displaying music file metadata in the
#       PDF display window.
# ---------------------------------------------------------------------------------------

# MYSQL = True
# SQLITE = False
# FULLTEXT = False        # /// RESUME - pass with option

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

    def set_elements( self, title, local, canonical, file, number, sheet, current_audio, current_midi ):
        self.title_ele = title
        self.local_ele  = local
        self.canonical_ele  = canonical
        self.file_ele  = file
        self.number_ele  = number
        self.sheet_ele  = sheet
        self.current_audio_ele = current_audio
        self.current_midi_ele = current_midi

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

    # --------------------------------------------------------------

    def process_events( self, event, values ):

        # ------------------------------------------------------------------
        #   User changed PDF page with icons, keystrokes, or scrolling
        #   Don't do anything if don't have database yet.

        if event == 'hidden-page-change':

            p = self.pdf.get_info()
            self.show_page_update(
                       page = p[ 'page' ],
                       page_count = p[ 'page_count' ],
                     )

            return False        # Others may want this event, too

        # ------------------------------------------------------------------

    # --------------------------------------------------------------
    #   Populate the supplied or found metadata info in PDF window and save a copy.
    #   Called after pdf.show_music_file() with all available parameters.
    #   Fill in missing if possible.
    #   Always have 'file', page, and page_count
    #   /// RESUME - After cleanup this still may be too complicated. Try to simplify?

    def show( self, id=None, file=None, page=None, sheet=None, src=None, local=None,
                    canonical=None, page_count=None, title=None ):

        titles_array = []
        # ---------------------------------------------------------------------------------

        self.info = {               # Save data from most recent call, need some for setlist, may need more later.
            'id' :          id,
            'file' :        file,
            'page' :        page,
            'sheet' :       sheet,
            'src' :         src,
            'local' :       local,
            'canonical' :   canonical,
            'title' :       title,
            'titles' :      None,
            'page_count' :  page_count,
        }

        # ----------------------------------------------------------------------

        # self.debug_metadata.update( value = id )
        # print( self.info )
        # print( '' )

        # ----------------------------------------------------------------------
        #   WRW 22 Jan 2022 - file is now partial path, i.e., without root to files.
        #   If no file given don't clear display, keep old value.
        #   File now always given but test anyway.

        if file:
            if '/' in file:
                files = file.split('/')
                file1 = '/'.join( files[ 0:-1] ) + '/'
                file2 = files[ -1]

            else:
                file1 = file
                file2 = ''

            self.file_ele.update( value = f'{file1}\n{file2}' )
        else:
            self.file_ele.update( value = f'' )

        # -------------------------------
        #   If don't have canonical may be able to get it from file, which we always have.

        if not canonical:
            canonical = self.fb.get_canonical_from_file( file )

            if canonical:
                self.info[ 'canonical' ] = canonical
                self.canonical_ele.update( value = canonical )
            else:
                self.canonical_ele.update( value = '' )
        else:
            self.canonical_ele.update( value = canonical )

        # -------------------------------
        #   Populate titles

        if src and local:
            self.local_ele.update( value = f"{local} - {src}" )

            #   Only get sheet if don't already have it.
            if not sheet:
                sheet = self.fb.get_sheet_from_page( page, src, local )

            if sheet:
                self.sheet_ele.update( value = f"Sheet: {sheet}" )
                self.info[ 'sheet'  ] = sheet

                titles_array = self.fb.get_titles_from_sheet( sheet, src, local )
                # print( f"/// titles: {titles_array}, '{sheet}', '{src}', '{local}'" )

                titles_text = '\n\n'.join( titles_array )

            else:
                self.sheet_ele.update( value = f"Sheet: - " )
                titles_array = []
                titles_text = ''

            self.title_ele.update( value = titles_text )
            self.info[ 'titles' ] = titles_array

        else:
            # ---------------------------------------------------------------------------------
            #   Don't have src/local, may be able to get it from canonical.

            #   WRW 24 Jan 2022 - Exploratory - Try to fill in missing src/local data.
            #   Most call profiles do not include it, only calling from Click in index music file table has it.
            #   Get one src/local pair from several possible from file
            #   I.e., map file back to canonical back to one src/local.

            if canonical:
                rows = self.fb.get_src_local_from_canonical( canonical )

                if len(rows):                   # Success getting src & local from canonical
                    src, local = rows[0]        # Ordered by src priority in sql.
                    self.info[ 'src' ] = src
                    self.info[ 'local' ] = local
                    self.local_ele.update( value = f"* {local} - {src}" )     # * signifies src by priority

                    if not sheet:
                        sheet = self.fb.get_sheet_from_page( page, src, local )

                    if sheet:
                        self.sheet_ele.update( value = f"Sheet: {sheet}" )
                        titles_array = self.fb.get_titles_from_sheet( sheet, src, local )
                        titles_text = '\n\n'.join( titles_array )

                    else:
                        self.sheet_ele.update( value = f"Sheet: - " )
                        titles_array = []
                        titles_text = ''

                    self.title_ele.update( value = titles_text )
                    self.info[ 'titles' ] = titles_array

                else:
                    self.title_ele.update( value = '' )
                    self.local_ele.update( value = '' )
                    self.sheet_ele.update( value = '' )

        # -------------------------------

        if page and page_count:
            self.number_ele.update( value = f"Page: {page} of {page_count}" )
        else:
            self.number_ele.update( value = '' )

        # -------------------------------

        self.update_current_midi( titles_array )
        self.update_current_audio( titles_array )

    # ---------------------------------------------------------------------------------------

    def OMIT_show_from_setlist( self, file, page, page_count, title, src, local, canonical ):
        self.info = {               # Save data from most recent call, need some for setlist, may need more later.
            'file' : file,
            'page' : page,
            'page_count' : page_count,
            'canonical' : canonical,
            'title' : title,

            'sheet' : None,
            'src' : src,
            'local' : local,
        }

        if '/' in file:
            files = file.split('/')
            file1 = '/'.join( files[ 0:-1] ) + '/'
            file2 = files[ -1]

        else:
            file1 = file
            file2 = ''

        self.file_ele.update( value = f"{file1}\n{file2}" )

        page = page if page else ''
        page_count = page_count if page_count else ''
        self.number_ele.update( value = f"Page: {page} of {page_count}" )

        canonical = canonical if canonical else ''
        self.canonical_ele.update( value = f"{canonical}" )

        title = title if title else ''
        self.title_ele.update( value = f"{title}" )

        self.update_current( [title] )

    # ---------------------------------------------------------------------------------------
    #   WRW 24 Jan 2022 - New page in existing document.

    def show_page_update( self, page, page_count ):

        if self.info[ 'src'] and self.info[ 'local' ]:
            src = self.info[ 'src'] 
            local = self.info[ 'local']

            sheet = self.fb.get_sheet_from_page( page, src, local )
            if sheet:
                self.sheet_ele.update( value = f"Sheet: {sheet}" )
                titles_ary = self.fb.get_titles_from_sheet( sheet, src, local )
                titles_text = '\n\n'.join( titles_ary )
            else:
                self.sheet_ele.update( value = f"Sheet: - " )
                titles_ary = []
                titles_text = ''

            self.title_ele.update( value = titles_text )
            self.local_ele.update( value = f"{local} - {src}" )

            self.info[ 'titles' ] = titles_ary
            self.update_current_audio( titles_ary )
            self.update_current_midi( titles_ary )

        else:
            self.title_ele.update( value = '' )
            self.local_ele.update( value = '' )
            self.sheet_ele.update( value = '' )
            self.update_current_audio( [] )
            self.update_current_midi( [] )

        self.number_ele.update( value = f"Page: {page} of {page_count}" )
        self.info[ 'page' ] = page

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

        # self.current_audio_ele.update( values = table )
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

        # self.current_audio_ele.update( values = table )
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
    #   /// RESUME Not useful so far. Getting too many matches. Perhaps LIKE.

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
#   WRW 18 Jan 2022 - Exploring table of contents of current book
#   WRW 22 Jan 2022 - Pulled out into separate module from bluebird.py

class TableOfContents():

    # -------------------------------
    def __init__( self ):
        self.current_src = None
        self.current_local = None

    # -------------------------------
    def set_elements( self, fb, book_titles ):
        self.fb = fb
        self.table_of_contents_ele = book_titles

        self.current_src = None
        self.current_local = None

    # -------------------------------
    #   Several call profiles
    #       toc.show()
    #       toc.show( src=src, local=local )
    #       toc.show( file=path )
    #       toc.show( canonical=canonical )

    #   /// RESUME - needs a little more thought, maybe separate show() functions.

    def show( self, file=None, src=None, local=None, canonical=None ):

        # ---------------------------------------
        #   Clear TOC

        if not file and not src and not local and not canonical:
            self.table_of_contents_ele.update( values = [] )

        # ---------------------------------------
        #   Simple case, get TOC from book index or index management table, toc indicated by src & local

        elif src and local:    # From Click in indexed music file table
            if self.current_src != src or self.current_local != local:
                self.current_src = src
                self.current_local = local
                self.book_titles_table_data = self.fb.get_table_of_contents( src, local )
                self.table_of_contents_ele.update( values = self.book_titles_table_data )

        # ---------------------------------------
        #   Get one src/local pair from several possible from canonical.
        #   I.e., map canonical back to one src/local.
        #   /// RESUME - issue here

        elif canonical:     # From Click in setlist
            rows = self.fb.get_src_local_from_canonical( canonical )

            if len(rows):
                src, local = rows[0]        # Ordered by src priority in sql.
                self.book_titles_table_data = self.fb.get_table_of_contents( src, local )
                self.table_of_contents_ele.update( values = self.book_titles_table_data )

            else:
                self.table_of_contents_ele.update( values = '' )

        # ---------------------------------------
        #   Get one src/local pair from several possible from file
        #   I.e., map file back to canonical back to one src/local.

        elif file:       # From Click in music file table or musie file browse tree.
            canonical =  self.fb.get_canonical_from_file( file.as_posix() )
            if canonical:
                rows = self.fb.get_src_local_from_canonical( canonical )
                if len(rows):
                    src, local = rows[0]        # Ordered by src priority in sql.
                    self.book_titles_table_data = self.fb.get_table_of_contents( src, local )
                    self.table_of_contents_ele.update( values = self.book_titles_table_data )
                else:
                    self.table_of_contents_ele.update( values = '' )

            else:
                self.table_of_contents_ele.update( values = '' )

    # -------------------------------
    #   Retrieve sheet number from toc
    #   toc: row[ 'title' ], row[ 'sheet' ]

    def get_sheet( self, index ):
        return self.book_titles_table_data[index][1]

# ---------------------------------------------------------------------------------------
