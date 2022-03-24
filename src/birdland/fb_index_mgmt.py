#!/usr/bin/python

# -----------------------------------------------------------------------------------------------

from pathlib import Path

# -----------------------------------------------------------------------------------------------

class Mgmt():

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

    def set_classes( self, conf, fb, pdf, meta, toc ):
        self.conf = conf
        self.fb = fb
        self.pdf = pdf
        self.meta = meta
        self.toc = toc

    # -----------------------------------
    #   Populate the src and local tables. Can't do this at init as don't have self.fb yet.

    def load_tables( self ):
        if self.table_loaded:
            return
        self.table_loaded = True

        self.srcs = self.fb.get_srcs()  
        # self.index_mgmt_src_table.update( values = self.srcs )
        self.fb.safe_update( self.index_mgmt_src_table, self.srcs )

    def set_class_config( self ):
        pass

    def process_events( self, event, values ):
        # print( "/// mgmt process_event:", event )

        # ------------------------------------------
        #   Click in sources table. Populate the locals table, clear info and main table.

        if event == 'index-mgmt-src-table':
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

        if event == 'index-mgmt-local-table':
            if( 'index-mgmt-src-table' in values and len( values[ 'index-mgmt-src-table' ] ) and
                'index-mgmt-local-table' in values and len( values[ 'index-mgmt-local-table' ] )
              ):

                self.local = self.locals[ values[ 'index-mgmt-local-table' ][0] ][0]
                index = self.fb.get_index_from_src_local( self.src, self.local )
                show_data = False

                # -----------------------------------------------
                #   Get a little more data to display and use for showing PDF file now that local is selected

                self.index_mgmt_info_src.update( value = self.src )
                self.index_mgmt_info_local.update( value = self.local )

                self.canonical = self.fb.get_canonical_from_src_local( self.src, self.local )
                if self.canonical:
                    self.index_mgmt_info_canonical.update( value = self.canonical )

                    self.file = Path( self.fb.get_file_from_canonical( self.canonical ) )

                    if self.file:
                        self.index_mgmt_info_file.update( value = self.file )
                        fullpath = Path( self.fb.Music_File_Root, self.file )

                        if not fullpath.is_file():
                            self.conf.do_nastygram( 'music_file_root', fullpath )
                            return

                        self.page_count = self.pdf.get_page_count( fullpath )

                        self.index_mgmt_info_page_count.update( value = self.page_count )
                        show_data = True

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
                    #   Some issues here still. Sheet is starting over at 1 after
                    #       several iterations. get_sheet_from_page doing it.
                    #       Resolved by returning None from get_sheet_from_page() and testing for None.
                    #   /// RESUME - think more about offsets, etc.

                    data = []
                    for page in range( 1, self.page_count + 1):
                        spage = str( page )
                        offset = self.fb.get_sheet_offset( spage, self.src, self.local )
                        sheet = str( self.fb.get_sheet_from_page( spage, self.src, self.local ) )

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

                    fullpath = Path( self.fb.Music_File_Root, self.file )
                    self.pdf.show_music_file( file=fullpath, page=1, force=True )                              

                    self.meta.show( id='IndexMgmtLoad',
                                    file=self.file.as_posix(),
                                    # title = title,
                                    canonical = self.canonical,
                                    src = self.src,
                                    local = self.local,
                                    sheet = 1,
                                    page=1,
                                    page_count = self.pdf.get_info()[ 'page_count' ],
                                  )


                    self.toc.show( src=self.src, local=self.local )

                # -----------------------------------------------
                #   No data to show, clear table of old data

                else:
                    # self.index_mgmt_table.update( values = [] )
                    self.fb.safe_update( self.index_mgmt_table, [] )
                    self.toc.show()     # Clear toc when no args.

            # -----------------------------------------------
            else:
                pass

            return True

        # ------------------------------------------
        #   Click in main index management table, show PDF at page.
        #   no toc.show(), already have toc up from above.

        if event == 'index-mgmt-table':
            if self.table_data:
                if "index-mgmt-table" in values and len( values[ "index-mgmt-table" ] ):
                    index = values[ "index-mgmt-table" ][0]

                    # table_data: (spage, sheet, offset, title, composer )

                    page = self.table_data[ index ][0]
                    sheet = self.table_data[ index ][1]
                    title = self.table_data[ index ][2]
                    composer = self.table_data[ index ][3]

                    fullpath = Path( self.fb.Music_File_Root, self.file )
                    self.pdf.show_music_file( file=fullpath, page=page, force=True )      # Click in Management Table
                    self.display_pdf.select()
                    self.display_pdf.set_focus()

                    self.meta.show( id='IndexMgmtClick',
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
