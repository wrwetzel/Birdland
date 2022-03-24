#!/usr/bin/python

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import sys

# -----------------------------------------------------------------------------------------------

class Diff():

    # --------------------------------------------------------------
    def __init__( self ):
        self.src = None
        self.local = None
        self.canonical = None
        self.table_loaded = False

    def set_elements( self, dc, info_canon, table, canon_table, display_pdf ):
        self.dc = dc
        self.index_diff_info_canonical = info_canon
        self.index_diff_table = table
        self.index_diff_canonical_table = canon_table
        self.display_pdf = display_pdf

    # -----------------------------------

    def set_classes( self, conf, sg, fb, pdf, meta, toc ):
        self.conf = conf
        self.sg = sg
        self.fb = fb
        self.pdf = pdf
        self.meta = meta
        self.toc = toc

    # -----------------------------------

    def set_icon( self, t ):
        global BL_Icon
        BL_Icon = t

    # ---------------------------------
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

    def do_bind( self ):
        self.index_diff_table.bind( '<Button-1>', '-Click' )

    # -----------------------------------
    def set_class_config( self ):
        pass

    # -----------------------------------
    def process_events( self, event, values ):

        # ------------------------------------------
        #   Click in canonicals table. Select book to show in main table.
        #   Change state of show-all radio box.
        
        if ( event == 'index-diff-canonical-table' or 
             event == 'index-diff-controls-1' or
             event == 'index-diff-controls-2' ):

            if( 'index-diff-canonical-table' in values and len( values[ 'index-diff-canonical-table' ] ) ):

                self.canonical = self.canonicals[ values[ 'index-diff-canonical-table' ][0] ][0]
                self.index_diff_info_canonical.update( value = self.canonical )

                data = self.fb.get_diff_data( self.canonical )
                show_data = False

                # ------------------------------------------------
                #   Build array of data by title

                self.src_list = set()
                titles = {}
                for row in data:
                    title = row['title']
                    if title not in titles:
                        titles[ title ] = []
                    titles[ title ].append(row )
                    self.src_list.add( row['src'] )

                self.src_list = sorted( self.src_list )
                table_data = []
                for title in titles:
                    data = self.inspect_data( title, self.src_list, titles[ title ] )

                    if values[ 'index-diff-controls-1' ] or data['same'] == '*':
                        table_row = []
                        table_row.append( data['title'] )
                        table_row.append( data['same'] )
                        res_by_src = data[ 'res_by_src' ]
                        for src in self.srcs:
                            if src in res_by_src:
                                table_row.append( res_by_src[src] )
                            else:
                                table_row.append( '' )
                        table_data.append( table_row )
                        show_data = True
                        
                if show_data:
                    # self.index_diff_table.update( values = table_data )
                    self.fb.safe_update( self.index_diff_table, table_data )

                else:
                    # self.index_diff_table.update( values = [] )
                    self.fb.safe_update( self.index_diff_table, [] )
                    self.toc.show()     # Clear toc when no args.

                self.table_data = table_data

            # -----------------------------------------------

            return True

        # ------------------------------------------
        #   Click in main index management table, show PDF at page.
        #   Identifying row & column of click is black magic from the innards of Tkinter.
        #   See example in Play/table-index.py, found it online.

        if event == 'index-diff-table-Click':

            if not self.canonical:
                self.sg.popup( f"\nPlease select a book from the canonical table\n",
                    title='Birdland Warning',
                    icon='BL_Icon',
                    line_width = 100,
                    keep_on_top = True,
                )
                return True

            event = self.index_diff_table.user_bind_event
            col = self.index_diff_table.Widget.identify_column( event.x )
            row_i = self.index_diff_table.Widget.identify_row( event.y )
            row = self.index_diff_table.Widget.item( row_i )

            col_num = int( col[1:])
            src = self.srcs[ col_num -3 ]               # -1 for title, -1 for M, and -1 since arrives one-based
            local = self.fb.get_local_from_canonical_src( self.canonical, src )

            if col_num < 3:                             # Ignore click in title or 'same' column
                return True

            if src not in self.src_list:                # Ignore click in empty column
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
                return True                             # Click in empty cell

            sheet, page = contents.split( '->' )
            sheet=sheet.strip()
            page=page.strip()
            file = self.fb.get_file_from_canonical( self.canonical )

            if not file:           
                self.conf.do_nastygram( 'canonical2file', None )
                return

            fullpath = Path( self.fb.Music_File_Root, file )

            if not fullpath.is_file():
                self.conf.do_nastygram( 'music_file_root', fullpath )
                return

            self.pdf.show_music_file( file=fullpath, page=page, force=True )      # Click in Management Table

            self.display_pdf.select()
            self.display_pdf.set_focus()

            # print( title, src, local, sheet, page, file )

            self.meta.show( id='IndexDiffClick',
                            file=file,
                            title = title,
                            canonical = self.canonical,
                            src = src,
                            local = local,
                            sheet = sheet,
                            page=page,
                            page_count = self.pdf.get_info()[ 'page_count' ],
                          )
            self.toc.show( src=src, local=local )

            return True


    # --------------------------------------------------------------------------
    #   Called with data for one title. Have to check all entries for one title together.
    #   Need to rearrange into canonical, sheet, src order so can see all sources for one canonical together.
    
    def inspect_data( self, title, src_list, data ):
    
        # -------------------------------------------
        #   Title may appear in more than one canonical. Only check for match in the indexes for one canonical at a time.
        #   First group by canonical.
    
        srcs = {}
        pages = []
    
        for item in data:
            title = title
            sheet = item['sheet']
            src =   item['src']
            local = item['local']
            page =  self.fb.get_page_from_sheet( sheet, src, local )
    
            if not page:
                print( f"ERROR-DEV: get_page_from_sheet() returned None, sheet: '{sheet}', src: '{src}', local: '{local}', skipping.", file=sys.stderr )
                continue
    
            srcs[ src ] = { 'sheet' : sheet, 'page': page }
            pages.append( page )
    
        same = all( x == pages[0] for x in pages )
        same_flag = ' ' if same else '*'
    
        # index_list = []
        res_by_src = {}
        for src in src_list:
            if src in srcs:
                item = srcs[ src ]
                # index_list.append( f"{src:>3} (s {item['sheet']:>3}) (p {item['page']:>3})" )
                res_by_src[ src ] = f"{item['sheet']:>3}->{item['page']:>3}"
            else:
                # index_list.append( f"    (s    ) (p    )" )
                res_by_src[ src ] = ''
    
        # index_list = '   '.join( index_list )
    
        short_title = title[0:30]
    
        res = { 'title' : short_title, 'same' : same_flag, 'res_by_src' : res_by_src }
        return res

        # print( f"{short_title:>50} {same_flag}:  {index_list}" )
    
    # --------------------------------------------------------------------------
    #   Round m to next larger multiple of n: k = m + n - m % n

    def show_offset_graph( self, src, local, page_count ):

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

        # -------------------------------------------------------
        #   Draw axis in absolute coordinates

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
        #   Draw x and y axis coordinates.

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
                    icon='BL_Icon',
                    line_width = 100,
                    keep_on_top = True,
                )


# -----------------------------------------------------------------------------------------------

