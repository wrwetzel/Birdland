#!/usr/bin/python

# -----------------------------------------------------------------------------------------------

from pathlib import Path

# -----------------------------------------------------------------------------------------------

class PageList():

    # --------------------------------------------------------------
    def __init__( self ):
        self.src = None
        self.local = None

    def set_elements( self, dc, table, src_table, local_table, info_src, info_local, info_canonical, info_file, display_pdf, info_page_count ):
        self.dc = dc
        self.index_mgmt_table = table
        self.index_mgmt_src_table = src_table
        self.index_mgmt_local_table = local_table
        self.srcs = []
        self.locals = []
        self.table_data = None
        self.src = None
        self.local = None
        self.index_mgmt_info_src = info_src
        self.index_mgmt_info_local = info_local
        self.index_mgmt_info_canonical = info_canonical
        self.index_mgmt_info_file = info_file
        self.index_mgmt_info_page_count = info_page_count
        self.display_pdf = display_pdf
        self.table_loaded = False

    # -----------------------------------

    def set_classes( self, conf, fb, pdf, meta, diff ):
        self.conf = conf
        self.fb = fb
        self.pdf = pdf
        self.meta = meta
        self.diff = diff

    # -----------------------------------

    def do_bind( self ):
        self.index_mgmt_table.bind( '<Button-1>', '-Click' )
        self.index_mgmt_table.bind( '<ButtonRelease-1>', '-Button-1-Up' )

    # -----------------------------------
    #   Populate the src and local tables. Can't do this at init as don't have self.fb yet.

    def load_tables( self ):
        if self.table_loaded:
            return
        self.table_loaded = True

        self.srcs = self.fb.get_srcs()  
        self.fb.safe_update( self.index_mgmt_src_table, self.srcs )

    def set_class_config( self ):
        pass

    def process_events( self, event, values ):
        # print( "/// index-mgmt:", event )

        # ------------------------------------------
        if event == 'index-mgmt-table-Button-1-Up':
            if self.diff.pdf_window:
                self.diff.pdf_window.close()
                return True

        # ------------------------------------------
        #   Click in sources table. Populate the locals table, clear info and main table.

        elif event == 'index-mgmt-src-table':
            if 'index-mgmt-src-table' in values and len( values[ 'index-mgmt-src-table' ] ):
                index = values[ 'index-mgmt-src-table' ][0]
                self.src = self.srcs[ index ]   
                self.locals = self.fb.get_locals_from_src( self.src )  

                # self.index_mgmt_local_table.update( values = self.locals )
                self.fb.safe_update( self.index_mgmt_local_table, self.locals )

                self.index_mgmt_info_src.update( value = self.src )
                self.index_mgmt_info_local.update( value = '' )
                self.index_mgmt_info_canonical.update( value = '' )
                self.index_mgmt_info_file.update( value = '' )
                self.index_mgmt_info_page_count.update( value = '')
                self.index_mgmt_table.update( values = [] )
            return True

        # ------------------------------------------
        #   Click in locals table. Select book to show in main table.

        elif event == 'index-mgmt-local-table':
            if( 'index-mgmt-src-table' in values and len( values[ 'index-mgmt-src-table' ] ) and
                'index-mgmt-local-table' in values and len( values[ 'index-mgmt-local-table' ] )
              ):

                self.local = self.locals[ values[ 'index-mgmt-local-table' ][0] ][0]
                index = self.fb.get_index_from_src_local( self.src, self.local )
                show_data = False

                # -----------------------------------------------
                #   Get a little more data to display and use for showing PDF file now that local is selected
                #   WRW 1 June 2022 - On virgin machine without canonical2file we should still populate the table
                #       as it looks like the music file is not even used here any more. No, need it to get
                #       page count at least.

                self.index_mgmt_info_src.update( value = self.src )
                self.index_mgmt_info_local.update( value = self.local )

                if not self.fb.Music_File_Root:
                #   WRW 1 June 2022 - Only noticed this when testing on virgin virtual machine.
                    t = f"'Root of music file' not defined in settings. Required to show page list."
                    self.conf.do_popup( t )
                    return True

                self.canonical = self.fb.get_canonical_from_src_local( self.src, self.local )
                if self.canonical:
                    self.index_mgmt_info_canonical.update( value = self.canonical )

                    t = self.fb.get_file_from_canonical( self.canonical )       # WRW 9 Apr 2022 - None sometimes.

                    if t:
                        self.file = Path( t )

                        if self.file:
                            self.index_mgmt_info_file.update( value = self.file )
                            fullpath = Path( self.fb.Music_File_Root, self.file )

                            if not fullpath.is_file():
                                self.conf.do_nastygram( 'music_file_root', fullpath )
                                return True

                            self.page_count = self.pdf.get_page_count( fullpath )

                            self.index_mgmt_info_page_count.update( value = self.page_count )
                            show_data = True

                        else:
                            self.index_mgmt_info_file.update( value = '' )
                    else:
                        self.index_mgmt_info_file.update( value = '' )

                else:
                    self.index_mgmt_info_canonical.update( value = '' )
                    self.index_mgmt_info_file.update( value = '' )
                    self.index_mgmt_info_page_count.update( value = '')

                # --------------------------
                #   Only populate main table when have src, local, canonical, and file

                if show_data:
                    items_by_sheet = {}

                    # -----------------------------------
                    #   Build new data structure from index contents. Possibly multiple titles per sheet.

                    for item in index:
                        sheet = item[ 'sheet' ]              # As specified in incoming index.
                        title = item[ 'title' ]
                        composer = item[ 'composer' ] if 'composer' in item else ''
                        items_by_sheet.setdefault( sheet, [] ).append( [ title, composer ] )

                    # -----------------------------------
                    #   Create an entry in table for every page, not just sheets in index.
                    #   Remember that page is numeric in DB so can do comparisons on it.
                    #   WRW 28 Apr 2022 - Switch to using page, not spage, for fb_utils calls below.

                    data = []
                    for page in range( 1, self.page_count + 1):
                        spage = str( page )

                      # offset = self.fb.get_sheet_offset_from_page( spage, self.src, self.local )
                        offset = self.fb.get_sheet_offset_from_page( page, self.src, self.local )

                      # sheet = str( self.fb.get_sheet_from_page( spage, self.src, self.local ) )
                        sheet = str( self.fb.get_sheet_from_page( page, self.src, self.local ) )

                        if sheet and sheet in items_by_sheet:
                            items = items_by_sheet[ sheet ]
                            for item in items:                      # Possible multiple songs on one page.
                                title = item[ 0 ]
                                composer = item[ 1 ]
                                data.append( (spage, sheet, offset, title, composer ))
                        else:
                            data.append( (spage, '', '', '', '' ))

                    # self.index_mgmt_table.update( values = data )
                    self.fb.safe_update( self.index_mgmt_table, data )
                    self.table_data = data

                    # -----------------------------------------------------------------------
                    #   WRW 29 Apr 2022 - See no need to load book in Music Viewer, can view
                    #       page of music by clicking in row. Save one meta.show() to deal with.

                    if False:

                        fullpath = Path( self.fb.Music_File_Root, self.file )
                        self.pdf.show_music_file( file=fullpath, page=1, force=True )

                        self.meta.show( id='IndexPageLoad',
                                        mode='N',                       # Not using this code
                                        file=self.file.as_posix(),
                                        # title = title,
                                        canonical = self.canonical,
                                        src = self.src,
                                        local = self.local,
                                        sheet = 1,
                                        page=1,
                                        page_count = self.pdf.get_info()[ 'page_count' ],
                                      )

                # -----------------------------------------------
                #   No data to show, clear table of old data

                else:
                    self.fb.safe_update( self.index_mgmt_table, [] )

            # -----------------------------------------------
            else:
                pass

            return True

        # ------------------------------------------
        #   Click in main index management table, show PDF at page.
        #   no toc.show(), already have toc up from above.
        #   table_data: (spage, sheet, offset, title, composer )
        #   WRW 26 Apr 2022 - Cleaning up warts - switched to approach used in fb_index_diff.py
        #       to identify page for pdf popup. Previous approach only worked with 'index-mgmt-table' event,
        #       not 'index-mgmt-table-Click' event, which caused the use of old data.
        #       I suspect this happened because click event happened before row was selected.
        #       Fixed bug when popup redisplayed when scroll down in table with down key.

        # elif event == 'index-mgmt-table':

        elif event == 'index-mgmt-table-Click':
            if self.table_data:

                #   Don't ask, I don't understand this low-level Tkinter stuff, but it works.

                bind_event = self.index_mgmt_table.user_bind_event
                row_i = self.index_mgmt_table.Widget.identify_row( bind_event.y )
                row = self.index_mgmt_table.Widget.item( row_i )
                row_num = row[ 'tags' ][0]

                sheet = self.table_data[ row_num ][1]
                page = self.table_data[ row_num ][0]
                self.diff.do_pdf_popup( self.canonical, page, sheet )

                if False and "index-mgmt-table" in values and len( values[ "index-mgmt-table" ] ):

                    index = values[ "index-mgmt-table" ][0]
                    page = self.table_data[ index ][0]

                    # --------------------------------------------------
                    #   WRW 17 Apr 2022 - Show popup of PDF, don't display in Music View tab

                    if True:
                        sheet = self.table_data[ index ][1]
                        self.diff.do_pdf_popup( self.canonical, page, sheet )

                    # --------------------------------------------------
                    #   Earlier code, show PDF in Music View tab.
                    else:
                        fullpath = Path( self.fb.Music_File_Root, self.file )
                        self.pdf.show_music_file( file=fullpath, page=page, force=True )      # Click in Management Table
                        self.display_pdf.select()
                        self.display_pdf.set_focus()

                        sheet = self.table_data[ index ][1]
                        title = self.table_data[ index ][2]
                      # composer = self.table_data[ index ][3]

                        self.meta.show( id='IndexPageClick',
                                        mode='N',                       # Not using this code
                                        file=self.file.as_posix(),
                                        title = title,
                                        canonical = self.canonical,
                                        src = self.src,
                                        local = self.local,
                                        sheet = sheet,
                                        page=page,
                                        page_count = self.pdf.get_info()[ 'page_count' ],
                                      )
            return True

# -----------------------------------------------------------------------------------------------
