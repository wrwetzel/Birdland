#!/usr/bin/python
# -----------------------------------------------------------------------------------------------
#   fb_index_diff.py - Functions for the 'Index Management->Index Comparison' tab.

#   WRW 7 May 2022 - Move raw index .csv files to 'Raw-Index' and build in 'Raw-Index' folder name here.

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import sys
import subprocess
import shutil
import fitz
import tempfile
import gzip
import os

# -----------------------------------------------------------------------------------------------

def most_common( a ):
    return max(set(a), key = a.count)

# -----------------------------------------------------------------------------------------------

class Diff():

    # --------------------------------------------------------------
    def __init__( self ):
        self.src = None
        self.local = None
        self.canonical = None
        self.table_loaded = False
        self.title_by_row = []
        self.pdf_window = None
        self.pdf_figure = None

    def set_elements( self, dc, info_canon, table, canon_table, display_pdf ):
        self.dc = dc
        self.index_diff_info_canonical = info_canon
        self.index_diff_table = table
        self.index_diff_canonical_table = canon_table
        self.display_pdf = display_pdf

    # -----------------------------------

    def set_classes( self, conf, sg, fb, pdf, meta ):
        self.conf = conf
        self.sg = sg
        self.fb = fb
        self.pdf = pdf
        self.meta = meta

    # -----------------------------------

    def set_icon( self, t ):
        global BL_Icon
        BL_Icon = t

    # -----------------------------------------------------------------------------------------------
    #   WRW 15 Apr 2022 - An open question if I should do this all here or in fb_pdf.py. Needs here
    #   are very simple. Extracted code from fb_pdf.py. /// RESUME - add error checking.
    #   This opens the PDF file, gets the indicated page, gets and returns page dimensions.
    #   saving the dlist for display in part2 after zoom is determined.
    
    def show_pdf_part1( self, canonical, page ):
    
        file = self.fb.get_file_from_canonical( canonical )
        if not self.fb.Music_File_Root:
        #   WRW 1 June 2022 - Only noticed this when testing on virgin virtual machine.
            t = f"'Root of music file' not defined in settings. Required to show PDF of music."
            self.conf.do_popup( t )
            return False, False


        path = Path( self.fb.Music_File_Root, file )

        #   WRW 1 June 2022 - Only noticed this when testing on virgin virtual machine.
        if not path.is_file():
            t = f"ERROR: PDF file {path.as_posix()} not found at show_pdf_part1()"
            self.conf.do_popup( t )
            return False, False

        self.doc = fitz.open( path )

        fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
        self.dlist = self.doc[ int(page) -1 ].get_displaylist()
        fitz.TOOLS.mupdf_display_errors(True)
        self.doc.close()                    # Done with doc after we get displaylist

        fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
        r = self.dlist.rect
        fitz.TOOLS.mupdf_display_errors(True)
        page_height = (r.br - r.tr).y
        page_width =  (r.tr - r.tl).x

        return page_width, page_height

    # --------------------------------------------------
    #   This adjust the image size according to zoom and shows it in graph_element

    def show_pdf_part2( self, zoom, graph_element ):
        zoom_matrix = fitz.Matrix( zoom, zoom )
        image = self.dlist.get_pixmap( alpha=False, matrix=zoom_matrix )

        if self.pdf_figure:
             graph_element.delete_figure( self.pdf_figure )

        self.pdf_figure = graph_element.draw_image( data = image.tobytes(), location = (0, 0) )
    
    # -----------------------------------------------------------------------------------------------
    #   /// RESUME - Can optimize this to eliminate multiple calls for same page, prep and show.
    #   WRW 1 June 2022 - Looks like not used.

    def get_pdf_dimensions( self, canonical, page ):
    
        file = self.fb.get_file_from_canonical( canonical )
        path = Path( self.fb.Music_File_Root, file )

        if not path.is_file():
            t = f"ERROR: PDF file {path.as_posix()} not found at get_pdf_dimensions()"
            self.conf.do_popup( t )
            return False

        doc = fitz.open( path )

        fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
        r = doc[ int(page) -1 ].get_displaylist().rect
        fitz.TOOLS.mupdf_display_errors(True)
        page_height = (r.br - r.tr).y
        page_width =  (r.tr - r.tl).x
        doc.close()
        return page_width, page_height

    # -----------------------------------------------------------------------------------------------
    #   Populate the canonical table. Can't do this at init as don't have self.fb yet.

    def load_tables( self ):
        if self.table_loaded:
            return
        self.table_loaded = True

        self.canonicals_data = self.fb.get_canonicals_with_index()
        self.canonicals = [ [x['canonical']] for x in self.canonicals_data ]
        # self.index_diff_canonical_table.update( values = self.canonicals  )
        self.fb.safe_update( self.index_diff_canonical_table, self.canonicals )
        self.srcs = self.fb.get_srcs()                                                            

    # -----------------------------------
    #   WRW 16 Apr 2022 - Want to get mouse release to remove popup of PDF display of clicked title.

    def do_bind( self ):
        self.index_diff_table.bind( '<Button-1>', '-Click' )
        self.index_diff_table.bind( '<Button-3>', '-Right-Click' )
        self.index_diff_table.bind( '<ButtonRelease-1>', '-Button-1-Up' )

    # -----------------------------------
    def set_class_config( self ):
        pass

    # ---------------------------------------------------------------------------------------------------------
    #   WRW 14 Apr 2022
    #   Display a window of all selected titles. User selects one. All others are mapped to that one
    #   throught file saved here.

    def do_titles_to_edit_window( self, titles_to_edit ):

        page = self.most_common_by_title[ titles_to_edit[0] ]

        values = [ [x] for x in titles_to_edit ]    # Each row must be in separate array.

        intro = """Select one title in table and click 'Save'.
All other titles in table will be mapped to the selected one 
the next time the raw index is processed."""

        intro_text = self.sg.Text( text=intro,
             font=("Helvetica", 10 ),
             pad = ((0,0), (0, 0)),
             justification='left',
            )

        titles_table = \
            self.sg.Table(
                key='titles-table',
                headings = [ "Title" ],
                font = ("Helvetica", 11),
                values = values,
                row_height = 25,
                col_widths = [ 60 ],
                num_rows = len( titles_to_edit ),
                auto_size_columns = False,  # Must be false for col_width to work.
                justification = 'left',
                pad=[(0, 0), (10, 0)],
                select_mode = None,
              # enable_events = True,
                expand_x = True,
                expand_y = True,
                hide_vertical_scroll = True,
            )

        b1 = self.sg.Button('Save',
            key='titles-button-save',
            font=("Helvetica", 9),
            pad=((0,0),(10,10)), )

        b2 = self.sg.Button('Cancel',
            key='titles-button-cancel',
            font=("Helvetica", 9),
            pad=((10,0),(10,10)), )

        page_width, page_height = self.show_pdf_part1( self.canonical, page )
        if not page_width or not page_height:
            return False

        graph_y_size = 600
        graph_x_size = int( graph_y_size * page_width/page_height )
        zoom = graph_x_size / page_width        # Fit width     Since now fitting to exact page fit width and height
      # zoom = graph_y_size / page_height       # Fit height    should be the same.

        titles_pdf_graph = \
            self.sg.Graph( (graph_x_size, graph_y_size ),
                key = 'titles-pdf-graph',
                graph_bottom_left=(0, graph_y_size),
                graph_top_right=(graph_x_size, 0),
                # background_color = GraphBackground,
                pad=((0,0),(0,0)),
            )

        table_column = \
            self.sg.Column(
                [
                    [ intro_text ],
                    [ titles_table ],
                    [ b1, b2 ],
                ],
                vertical_alignment='Top',
                justification='left',
                element_justification='left',
                pad=((10,0),(10,0)),
            )

        graph_column = \
            self.sg.Column(
                [
                    [ titles_pdf_graph],
                ],
                vertical_alignment='Top',
                justification='left',
                element_justification='right',
                pad=((20,10),(10,10)),
            )

        titles_layout = [[ table_column, graph_column ]]

        titles_window = self.sg.Window( 'Select One from Similar Titles',
             return_keyboard_events=False,
             resizable=True,
             icon=BL_Icon,
             finalize = True,
             layout=titles_layout,
             keep_on_top = True,
            )

        self.show_pdf_part2( zoom, titles_window[ 'titles-pdf-graph' ] )

        # ------------------------------------------
        #   EVENT Loop for titles edit window.

        while True:
            event, values = titles_window.Read( )
    
            if event == self.sg.WINDOW_CLOSED:
                return False
    
            elif event == 'titles-button-cancel':
                titles_window.close()
                return False
    
            elif event == 'titles-button-save':
                if not values['titles-table']:
                    t = "Please select a title in table to map or click 'Cancel'"
                    self.conf.do_popup( t )
                    continue

                else:
                    row = values['titles-table'][0]
                    # print( "Selected:", titles_to_edit[ row ] )
                    selected = titles_to_edit[ row ]

                    others = [ titles_to_edit[ x ] for x in range( 0, len( titles_to_edit )) if x != row ]
                    # print( "Others:", others )

                    ofile = Path( self.conf.val( 'corrections' )).with_suffix( '.A.txt' )
                    with open( ofile, "a" ) as fo:
                        for other in others:
                            print( f"{other} | {selected} | {self.canonical}", file=fo )

                titles_window.close()
                return True

    # ---------------------------------------------------------------------------------------------------------
    # graph_x_size = int( graph_y_size * 9.0/12.0 )

    def do_pdf_popup( self, canonical, page, sheet=None ):

        page_width, page_height = self.show_pdf_part1( canonical, page )
        if not page_width or not page_height:
            return      

        graph_y_size = 600
        graph_x_size = int( graph_y_size * page_width/page_height )
        zoom = graph_x_size / page_width        # Fit width     Since now fitting to exact page fit width and height
      # zoom = graph_y_size / page_height       # Fit height    should be the same.

        #   Build sg.Graph() using dimensions above.

        page_number = \
            self.sg.Text( text= f"PDF Page: {page}",
                 font=("Helvetica", 11 ),
                 pad=((0,0), (0, 10)),
                 expand_x = True,
                 text_color = 'black',
                 background_color = '#e0e0ff',
                )

        sheet_number = \
            self.sg.Text( text= f"Sheet: {sheet}",
                 font=("Helvetica", 11 ),
                 pad=((0,0), (0, 10)),
                 expand_x = True,
                 text_color = 'black',
                 background_color = '#e0e0ff',
                 justification = 'right',
                )

        pdf_graph = \
            self.sg.Graph( (graph_x_size, graph_y_size ),
                key = 'pdf-graph',
                graph_bottom_left=(0, graph_y_size),
                graph_top_right=(graph_x_size, 0),
                pad=((0,0),(0,0)),
            )

        layout = [ [page_number, sheet_number], [ pdf_graph ]]

        self.pdf_window = self.sg.Window( '-',
             return_keyboard_events=False,
             resizable=True,
             icon=BL_Icon,
             finalize = True,
             layout=layout,
             keep_on_top = True,
             no_titlebar = True,
             margins = (10, 10),
             background_color = '#e0e0ff',
            )

        self.show_pdf_part2( zoom, self.pdf_window[ 'pdf-graph' ] )

        # ------------------------------------------
        #   No EVENT Loop for pdf popup window.
        #   Return here and process 'index-diff-table-Button-1-Up' event
        #       in process_events().

        return

    # ---------------------------------------------------------------------------------------------------------

    def process_events( self, event, values ):

        # ------------------------------------------
        #   WRW 16 Apr 2022 - Remove pdf_window on mouse release.

        if event == 'index-diff-table-Button-1-Up':
            if self.pdf_window:
                self.pdf_window.close()
                return True

        # ------------------------------------------
        #   Click in canonicals table. Select book to show in main table.
        #   Change state of show-all radio box.
        
        if ( event == 'index-diff-canonical-table' or 
             event == 'index-diff-controls-1' or
             event == 'index-diff-controls-2' or
             event == 'index-diff-controls-3' ):

            if( 'index-diff-canonical-table' in values and len( values[ 'index-diff-canonical-table' ] ) ):

                self.canonical = self.canonicals[ values[ 'index-diff-canonical-table' ][0] ][0]
                self.index_diff_info_canonical.update( value = self.canonical )

                data = self.fb.get_diff_data( self.canonical )
                show_data = False

                # ------------------------------------------------
                #   One pass over data to build array by title and accumulate all srcs covering canonical.
                #   WRW 1 Apr 2022 - Add partial coverage identification. Sort titles as dicts are not sorted.
                #       Also build new list with titles ordered same as in display table.

                self.src_list = set()               # All srcs covering canonical
                titles = {}                         # All titles from all srcs covering canonical
                self.scatter_by_src = {}            # WRW 4 Apr 2022 - collecting data for scatter plot.

                for row in data:                    # Put is dict indexed by title.
                    titles.setdefault( row['title'], [] ).append( row )
                    self.src_list.add( row['src'] )
                    page = self.fb.get_page_from_sheet( row[ 'sheet' ], row[ 'src' ], row[ 'local'] )        # Applies sheet offset to get page from sheet

                    self.scatter_by_src.setdefault( row['src'], [] ).append( { 'page' : page, 'sheet' : row['sheet'] } )

                self.src_list = set( sorted( self.src_list ) )      # sorted() returns list, must convert back to set().

                self.title_by_row = []
                self.srcs_by_row = []
                self.most_common_by_title = {}

                # ------------------------------------------------

                table_data = []                                     # Build entire table
                for title in sorted( titles ):
                    data = self.inspect_data( title, self.src_list, titles[ title ] )
                    partial_coverage = False if data[ 'srcs' ] == self.src_list else True
                    self.most_common_by_title[ title ] = data[ 'most_common' ]

                    if( values[ 'index-diff-controls-1' ] or                          # Show all
                        values[ 'index-diff-controls-2' ] and data['same'] == '*' or  # or show mismatches.
                        values[ 'index-diff-controls-3' ] and partial_coverage        # or show partial coverage
                      ):
                        self.title_by_row.append( title )       # WRW 1 Apr 2022 - Save for click on short title.
                        self.srcs_by_row.append( data[ 'srcs' ] )

                        table_row = []                              # Build one row of table
                        table_row.append( data['short_title'] )
                        table_row.append( data['same'] )
                        res_by_src = data[ 'res_by_src' ]
                        for src in self.srcs:                       # Build up horizontal row of page->sheet for each src.
                            t = res_by_src[src] if src in res_by_src else ''
                            table_row.append( t )
                        table_data.append( table_row )
                        show_data = True
                        
                if show_data:
                    self.fb.safe_update( self.index_diff_table, table_data )

                else:
                    self.fb.safe_update( self.index_diff_table, [] )

                self.table_data = table_data

            # -----------------------------------------------

            return True

        # ------------------------------------------
        #   Click in main index management table, show PDF at page.
        #   Identifying row & column of click is black magic from the innards of Tkinter.
        #   See example in Play/table-index.py, found it online.

        #   Left-click on populated table cell: Show the page.
        #   Left-click on title: Launch editor for entire line.
        #   Right-click on a populated table cell: Launch editor just for the index source
        #       for that cell, not whole line.
        # --------------------------------------------------------------------------

        if event == 'index-diff-table-Click' or event == 'index-diff-table-Right-Click':

            if event == 'index-diff-table-Click':
                click = 'Left'
            else:
                click = 'Right'

            if not self.canonical:
                self.sg.popup( f"\nPlease select a book from the canonical table\n",
                    title='Birdland Warning',
                    icon=BL_Icon,
                    line_width = 100,
                    keep_on_top = True,
                )
                return True

            # -----------------------------------------------------
            #   Gather some data common to all actions here.

            bind_event = self.index_diff_table.user_bind_event
            col = self.index_diff_table.Widget.identify_column( bind_event.x )
            row_i = self.index_diff_table.Widget.identify_row( bind_event.y )
            row = self.index_diff_table.Widget.item( row_i )

            col_num = int( col[1:])
            src = self.srcs[ col_num -3 ]               # -1 for title, -1 for M, and -1 since arrives one-based
            local = self.fb.get_local_from_canonical_src( self.canonical, src )

            # -----------------------------------------------------
            #   WRW 14 Apr 2022 - Lots of titles that should be the same differ in small ways. Need a quick way
            #       to select one and add all the rest to a map table for use on subsequent raw processing.

            #   It appears that this event fires before the clicked element is actually selected.
            #   Respond to Left Click so event doesn't propagate.

            if( click == 'Left' and                                                                      
                col_num == 1    and
                values[ 'index-diff-edit-titles' ] ):           # Left click on title in editing mode.
                return True

            # -----------------------------------------------------
            #   Same logic copied below for event == 'index-diff-select-button'

            if( click == 'Right' and
                col_num == 1    and
                values[ 'index-diff-edit-titles' ] ):            # Right click on title in editing mode.

                selected_rows = values[ "index-diff-table" ]
                if len( selected_rows ) < 2:                   # Nothing selected
                    return True

                titles_to_edit = [ self.title_by_row[ row ] for row in selected_rows ]

                self.do_titles_to_edit_window( titles_to_edit )
                self.index_diff_table.update( select_rows = [] )

                return True

            # -----------------------------------------------------
            #   WRW 1 Apr 2022 - As I start to actually use Birdland for cleaning up the raw indexes I was spending a lot of
            #       time just getting to the indexes. Add click on title to bring up editor for all srcs on line.

            elif( click == 'Right' and
                col_num == 1    and
                not values[ 'index-diff-edit-titles' ] ):            # Click on title not in editing mode.

                if 'tags' not in row or len( row[ 'tags' ] ) == 0:   # Click below filled rows
                    return True

                row_num = row[ 'tags' ][0]
                title = self.title_by_row[ row_num ]
                srcs = self.srcs_by_row[ row_num ]
                paths = []
                line_number = None

                for src in srcs:
                    source = self.fb.get_source_from_src( src )
                    raw_folder = self.conf.val( 'folder', source )
                    local = self.fb.get_local_from_canonical_src( self.canonical, src )
                    raw_file, tline = self.fb.get_raw_file( title, local, src )
                    if not line_number:        # Fetch first line number        
                        line_number = tline

                    if not raw_folder:
                        print( f"ERROR-DEV: Unexpected empty value for raw_folder for source {source}" )
                        sys.exit(1)

                    if not raw_file or not tline:
                        print( f"ERROR-DEV: Unexpected empty value for raw_file or tline for src {src} and title {title}" )
                        sys.exit(1)

                    paths.append( Path( raw_folder, 'Raw-Index', raw_file ) )   # WRW 7 May 2022 - build in 'Raw-Index' folder name.

                editor = self.conf.val( 'raw_index_editor' )
                ln_option = self.conf.val( 'raw_index_editor_line_num' )

                if not editor:
                    t = f"No Text Editor for raw index given in config file"
                    self.conf.do_popup( t )

                elif shutil.which( editor ):

                    # --------------------------
                    # Raw index may be compressed, e.g., Buffalo. Make a temp file to edit

                    epaths = []                         # Paths to edit
                    cpaths = []                         # Save to recompress

                    for path in paths:
                        if path.suffix == '.gz':
                            tfile = tempfile.mkstemp()
                            epath = tfile[1]
                            with gzip.open( path.as_posix(), 'rt' ) as ifd, open( epath, 'w' ) as ofd:
                                for line in ifd:
                                    ofd.write( line )
                            epaths.append( epath )
                            cpaths.append( { 'epath' : epath, 'path' : path } )

                        else:
                            epaths.append( path.as_posix() )

                    # --------------------------

                    ln_option_full = ln_option.replace( '?', line_number ).split()
                    command = [ editor, *ln_option_full, *epaths ]
                    po = subprocess.Popen( command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )
                    po.wait()

                    # --------------------------------------

                    for cpath in cpaths:
                        with open( cpath[ 'epath' ] ) as ifd, gzip.open( cpath[ 'path' ].as_posix(), 'wt' ) as ofd:
                            for line in ifd:
                                ofd.write( line )
                        os.remove( cpath[ 'epath' ] )

                    # --------------------------------------


                else:
                    t = f"Text Editor for raw index in config file '{editor}' not found."
                    self.conf.do_popup( t )

                return True

            # -----------------------------------------------------
            #   Right-Click in main body of table. Edit one raw index source file.

            elif click == 'Right':

                if col_num < 3:                    #   Ignore click in title or 'same' column
                    return True                             

                if src not in self.src_list:        #   Ignore click in empty column
                    return True

                if not row['values']:                       #   WRW 11 Apr 2022
                    return True                             #   Ignore right click in header

                contents = row['values'][int(col[1:])-1]                     
                if not contents:
                    return True                             # Ignore click in empty cell

                row_num = row[ 'tags' ][0]
                title = self.table_data[ row_num ][ 0 ]

                source = self.fb.get_source_from_src( src )
                raw_folder = self.conf.val( 'folder', source )
                local = self.fb.get_local_from_canonical_src( self.canonical, src )
                raw_file, line_number = self.fb.get_raw_file( title, local, src )

                if not raw_folder:
                    print( f"ERROR-DEV: Unexpected empty value for raw_folder for source {source}" )
                    sys.exit(1)

                if not raw_file or not line_number:
                    print( f"ERROR-DEV: Unexpected empty value for raw_file or line for src {src} and title {title}" )
                    sys.exit(1)

                path = Path( raw_folder, 'Raw-Index', raw_file )     # WRW 7 May 2022 - build in 'Raw-Index' folder name.
                editor = self.conf.val( 'raw_index_editor' )
                ln_option = self.conf.val( 'raw_index_editor_line_num' )

                if not editor:
                    t = f"No Text Editor for raw index given config file"
                    self.conf.do_popup( t )

                elif shutil.which( editor ):

                    # Raw index may be compressed, e.g., Buffalo. Make a temp file to edit

                    if path.suffix == '.gz':
                        compressed = True
                        tfile = tempfile.mkstemp()
                        epath = tfile[1]
                        with gzip.open( path.as_posix(), 'rt' ) as ifd, open( epath, 'w' ) as ofd:
                            for line in ifd:
                                ofd.write( line )

                    else:
                        epath = path.as_posix()
                        compressed = False

                    ln_option_full = ln_option.replace( '?', line_number ).split()
                    command = [ editor, *ln_option_full, epath ]
                    po = subprocess.Popen( command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )
                    po.wait()

                    if compressed:
                        with open( epath ) as ifd, gzip.open( path.as_posix(), 'wt' ) as ofd:
                            for line in ifd:
                                ofd.write( line )
                        os.remove( epath )

                else:
                    t = f"Text Editor for raw index in config file '{editor}' not found."
                    self.conf.do_popup( t )

                return True

            # -----------------------------------------------------
            #   Left-Click in main body of table.

            elif click == 'Left':

                if col_num < 3:     #   Ignore click in title or 'same' column
                    return True                             

                # -----------------------------------------------------
                #   Ignore click in empty column

                if src not in self.src_list:                
                    return True

                # -----------------------------------------------------

                if not row[ 'tags' ]:                        # Click in column headers, show offset graph
                    file = self.fb.get_file_from_canonical( self.canonical )

                    if not file:
                        self.conf.do_nastygram( 'canonical2file', None )
                        return

                    fullpath = Path( self.fb.Music_File_Root, file )

                    if not fullpath.is_file():
                        self.conf.do_nastygram( 'music_file_root', fullpath )
                        return

                    page_count = self.pdf.get_page_count( fullpath )
                    self.show_offset_graph( src, local, page_count )
                    return True

                # -----------------------------------------------------

                contents = row['values'][int(col[1:])-1]
                row_num = row[ 'tags' ][0]

                title = self.table_data[ row_num ][ 0 ]

                if not contents:
                    return True                             # Ignore click in empty cell

                sheet, page = contents.split( '->' )
                sheet=sheet.strip()
                page=page.strip()

                # ----------------------------------------------------------------
                #   WRW 15 Apr 2022 - Try popup of PDF instead of going to PDF Tab.

                if True:
                    self.do_pdf_popup( self.canonical, page, sheet )
                    return True

                else:
                    file = self.fb.get_file_from_canonical( self.canonical )

                    if not file:
                        self.conf.do_nastygram( 'canonical2file', None )
                        return

                    fullpath = Path( self.fb.Music_File_Root, file )

                    if not fullpath.is_file():
                        self.conf.do_nastygram( 'music_file_root', fullpath )
                        return True

                    self.pdf.show_music_file( file=fullpath, page=page, force=True )      # Click in Management Table

                    self.display_pdf.select()
                    self.display_pdf.set_focus()

                    # print( title, src, local, sheet, page, file )

                    self.meta.show( id='IndexDiffClick',
                                    mode='N',                       # Not using this code
                                    file=file,
                                    title = title,
                                    canonical = self.canonical,
                                    src = src,
                                    local = local,
                                    sheet = sheet,
                                    page=page,
                                    page_count = self.pdf.get_info()[ 'page_count' ],
                                  )
                    return True

        # -------------------------------------------
        #   Button does same thing as click on left click in select mode

        elif event == 'index-diff-select-button':
            selected_rows = values[ "index-diff-table" ]
            if len( selected_rows ) < 2 :                   # Nothing selected
                return True

            titles_to_edit = [ self.title_by_row[ row ] for row in selected_rows ]

            self.do_titles_to_edit_window( titles_to_edit )
            self.index_diff_table.update( select_rows = [] )

            return True

        # -------------------------------------------
        #   Didn't recognize any of our events.

        return False

    # --------------------------------------------------------------------------
    #   Called with data for one title. Have to check all entries for one title together.
    #   Need to rearrange into canonical, sheet, src order so can see all sources for one canonical together.
    #   src_list is sorted list of all srcs covered by canoical formed from set()
    #   Returns a truncated title, an indication of page mismatch (same == '*'), and list of pages offsets
    #        for srcs covering title, blanks if not, and a set of srcs covering this specific title.
    #   WRW 1 Apr 2022 - include title and short_title in results. Was just short_title as title.
    
    def inspect_data( self, title, src_list, data ):
    
        # -------------------------------------------
        #   Title may appear in more than one canonical. Only check for match in the indexes for one canonical at a time.
        #   First group by canonical.
    
        sp_by_srcs = {}
        pages = []
        srcs = set()
    
        #   Build array of sheet and page indexed by src and array of all page numbers for title.
        #       Page numbers should all be the same for a given title and canonical. If they are
        #       not it is because of mismatch in the index from different srcs.

        for item in data:
            title = title
            sheet = item['sheet']
            src =   item['src']
            local = item['local']
            page =  self.fb.get_page_from_sheet( sheet, src, local )        # Applies sheet offset to get page from sheet
    
            if not page:
                print( f"ERROR-DEV: get_page_from_sheet() returned None, title: '{title}', sheet: '{sheet}', src: '{src}', local: '{local}', skipping.", file=sys.stderr )
                continue
    
            sp_by_srcs[ src ] = { 'sheet' : sheet, 'page': page }   # Coverage of title by src
            pages.append( page )                                    # Page numbers of title from each src
            srcs.add( src )                                         # srcs covering title
    
        same = all( x == pages[0] for x in pages )                  # Test to see if all pages are the same
        same_flag = ' ' if same else '*'
    
        res_by_src = {}                                             
        for src in src_list:                                        # Traverse all srcs covering canonical
            if src in sp_by_srcs:                                   # Is this title covered by src
                item = sp_by_srcs[ src ]                            # Yes, pick up sheet/page
                res_by_src[ src ] = f"{item['sheet']:>3}->{item['page']:>3}"  # and include it in result.
            else:
                res_by_src[ src ] = ''                              # Otherwise include empty string in result
    
        short_title = title[0:40]       # *** Truncating title here. 31 Mar 2022 was 30
        most_common_page = most_common( pages )                     # Likely correct page.
    
        res = { 'title': title, 
                'short_title' : short_title,
                'same' : same_flag,
                'res_by_src' : res_by_src,
                'srcs' : srcs,
                'most_common' : most_common_page,
              }

        return res

        # print( f"{short_title:>50} {same_flag}:  {index_list}" )
    
    # --------------------------------------------------------------------------
    #   Round m to next larger multiple of n: k = m + n - m % n

    def show_offset_graph( self, src, local, page_count ):

        # -------------------------------------------------------
        #   For offset graph

        o_min = 9999999
        o_max = -9999999

        offsets = self.fb.get_offsets( src, local )
        for o in offsets:
            o_min = min( o_min, o[ 'offset' ] )
            o_max = max( o_max, o[ 'offset' ] )

        y_range = max( 5, o_max, abs( o_min ) )  # Make sure have some graph even when 0 range.
        y_range = y_range + 2 - y_range % 2    # Round up to next highest multiple of 2

        y_margin = 20   # top and bottom
        x_margin = 20   # left and right
        y_scale = 10    # apply to offsets to make them more aparent

        y_size = 2* y_range * y_scale
        x_size = page_count               

        x_total = x_size + 2 * x_margin
        y_total = y_size + 2 * y_margin

        # -------------------------------------------------------
        #   For scatter plot
        #   x and y are so close that can use one value for max of both

        scat_max = -9999999

        scatter_data = []
        for p in self.scatter_by_src[ src ]:
            x = int(p[ 'sheet' ])                       # x, y assigned here.
            y = int(p[ 'page'])
            scatter_data.append( (x,y) )
            scat_max = max( scat_max, x )
            scat_max = max( scat_max, y )

        scat_range = scat_max
        scat_x_size = scat_max          
        scat_y_size = scat_max

        scat_x_total = scat_x_size + 2 * x_margin
        scat_y_total = scat_y_size + 2 * y_margin

        # -------------------------------------------------------
        #   Build graph in absolute coordinates. Put y0 in middle.

        layout = [[
            self.sg.Graph( (x_total, y_total ),
                key = 'sheet-offset-graph',
                graph_bottom_left=(0, -y_total/2 ),
                graph_top_right=(x_total, y_total/2),
                background_color = "#f0f0ff",
                enable_events = True,
                # motion_events = True,     # not distributed copy yet
                # expand_x = True,
                # expand_y = True,
                pad= ((4, 4), (8,8)),
            ),

            self.sg.Graph( (scat_x_total, scat_y_total ),
                key = 'sheet-offset-scatter-chart',
                graph_bottom_left=(0, 0 ),
                graph_top_right=(scat_x_total, scat_y_total),
                background_color = "#f0f0ff",
                enable_events = True,
                # motion_events = True,     # not distributed copy yet
                # expand_x = True,
                # expand_y = True,
                pad= ((4, 4), (8,8)),
            )
        ],
            [ self.sg.Button('Close',  key='sheet-offset-close',  font=("Helvetica", 10), pad=((2,2),(2,1)), ) ]
        ]

        window = self.sg.Window( "Sheet-Offset Graph - PDF page number = sheet number + offset",
                 layout,
                 icon= BL_Icon,
                 finalize=True,
                 element_justification = 'right',
                 modal = True,
                )

        graph = window['sheet-offset-graph']
        scatter = window['sheet-offset-scatter-chart']          # WRW 5 Apr 2022 - a bit of an experiment

        # -------------------------------------------------------
        #   Draw axis in absolute coordinates for graph

        graph.draw_line(
            ( x_margin, 0),
            ( x_margin + x_size, 0),
            color = '#a0a0a0',
            width = 1,
        )

        graph.draw_line(
            ( x_margin, -y_size/2 ),
            ( x_margin,  y_size/2 ),
            color = '#a0a0a0',
            width = 1,
        )

        # -------------------------------------------------------
        #   Draw axis in absolute coordinates for scatter

        scatter.draw_line(
            ( x_margin, y_margin),
            ( x_margin + scat_x_size, y_margin),
            color = '#a0a0a0',
            width = 1,
        )

        scatter.draw_line(
            ( x_margin, y_margin),
            ( x_margin, scat_y_size + y_margin),
            color = '#a0a0a0',
            width = 1,
        )

        #   Experimental - draw diag red line through 0,0 as reference for offset

        scatter.draw_line(
            ( x_margin, y_margin),
            ( x_margin + scat_x_size, scat_y_size + y_margin),
            color = '#ff0000',
            width = .5,
        )

        # -------------------------------------------------------
        #   Draw x and y axis coordinates for graph

        for y in range( -y_range, y_range + 1, 2):

            graph.draw_text( str(y),
                ( x_margin/2, y * y_scale ),
                color = "black",
                font = ("Helvetica", 8),
                angle = 0,
                text_location = "center")

            color = '#000000' if y == 0 else '#e0e0e0'
            graph.draw_line(
                (x_margin,         y * y_scale ),
                (x_margin+x_size,  y * y_scale ),
                color = color,
                width = 1,
            )

        for x in range( 0, page_count, 50):
            graph.draw_text( str(x),
                ( x + x_margin, -y_size/2 - y_margin/2 ),
                color = "black",
                font = ("Helvetica", 8),
                angle = 0,
                text_location = "center")

            graph.draw_line(
                ( x + x_margin,  -y_size/2 ),
                ( x + x_margin,  y_size/2  ),
                color = '#e0e0e0',
                width = 1,
            )


        # -------------------------------------------------------
        #   Draw x and y axis coordinates for scatter

        for y in range( 0, scat_range + 1, 50):

            scatter.draw_text( str(y),                      # Labels on y axis
                ( x_margin/2, y + y_margin),
                color = "black",
                font = ("Helvetica", 8),
                angle = 0,
                text_location = "center")

            color = '#000000' if y == 0 else '#e0e0e0'
            scatter.draw_line(                              # Horizontal grid lines
                (x_margin,         y + y_margin ),
                (x_margin+scat_x_size,  y + y_margin ),
                color = color,
                width = 1,
            )

        for x in range( 0, scat_range, 50):                 # Labels on x axis
            scatter.draw_text( str(x),
                ( x + x_margin, y_margin/2 ),
                font = ("Helvetica", 8),
                color = "black",
                angle = 0,
                text_location = "center")

            color = '#000000' if x == 0 else '#e0e0e0'
            scatter.draw_line(                              # Vertial grid lines
                ( x + x_margin,  y_margin ),
                ( x + x_margin,  scat_y_size + y_margin ),
                color = color,
                width = 1,
            )


        # -------------------------------------------------------
        #   Shift to axis coordinates to draw graph
        #   Coordinates used here are as defined in Graph() above, i.e., with y0 in middle.

        # graph.draw_point( (0,0), size=10, color='red' )

        if False:       # Does not appear to be working. Make toy test. Do shifts manually for now.
            graph.change_coordinates(
                # (x_margin, -y_size/2 + y_margin),           # bottom left
                # (x_margin + x_size, y_size + y_margin )     # top right
                (x_margin, -y_size),           # bottom left
                (x_margin + x_size, y_size )     # top right
            )

        # graph.draw_point( (x_margin,0), size=10, color='yellow' )

        sx = x_margin
        sy = 0

        # -------------------------------------------------------
        #   Draw active part of graph.

        ox = 0
        for x in range( 1, page_count ):
            y = 0
            for o in offsets:
                if x >= o['start']:
                    y = o['offset']
                    break

            graph.draw_line(
                (ox + sx, y * y_scale + sy ),
                (x + sx,  y * y_scale + sy ),
                color = '#ff0000',
                width = 2,
            )
            ox=x

        # -------------------------------------------------------
        #   Draw active part of scatter
        #      scatter_by_src.setdefault( row['src'], [] ).append( { 'page' : page, 'sheet' : row['sheet'] } )

        sx = x_margin
        sy = y_margin

        for p in scatter_data:
            scatter.draw_point(
                (p[0] + sx, p[1] + sy ),
                color = '#000000',
                size = 2,
            )

        # -------------------------------------------------------
        #   Event loop for offset graph

        while True:
            event, values = window.Read( )
            if event == self.sg.WINDOW_CLOSED:
                break

            elif event == 'sheet-offset-close':
                window.close()
                break

            elif event == 'sheet-offset-graph+MOVE':
                print( values[ 'sheet-offset-graph+MOVE' ] )

            elif event == 'sheet-offset-graph':
                mx, my = values[ 'sheet-offset-graph' ]
                mx -= x_margin
                my = round( my/y_scale)

                self.sg.popup( f"\nApproximate Page Number: {mx}\n\nSheet Offset: {my}\n\n",
                    title='Birdland Note',
                    icon=BL_Icon,
                    line_width = 100,
                    keep_on_top = True,
                )


# -----------------------------------------------------------------------------------------------

