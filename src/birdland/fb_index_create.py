#!/usr/bin/python
# -----------------------------------------------------------------------------------------------
#   fb_index_create.py
#   WRW 17 Apr 2022 - Taken from fb_index_diff.py
#   WRW 24 Apr 2022 - Looks to be feature complete with even a little eye candy.
#   WRW 26 Apr 2022 - The canonical table had focus, even when I clicked on the pdf graph. Resolved
#       by explicitly giving graph focus when click on it.
#   WRW 27 Apr 2022 - Don't use fb_pdf.py keystroke processing - can't easily/cleanly synchronize it
#       to the page without also clearing the sheet on the next page. Just bind() a couple of keys here.
#   WRW 29 Apr 2022 - Changed name from fb_create_index.py to fb_index_create.py for consistency with
#       other index management modules.

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import sys
import subprocess
import shutil
import fitz
import csv
import io

import fb_pdf
import fb_title_correction

# -----------------------------------------------------------------------------------------------
#   26 Apr 2022 - Parameterize a few colors

Auto_OCR_Save_Color = '#00ff00'
Auto_OCR_Skip_Color = '#00ffff'
Manual_OCR_Color =    '#ff0000'

# -----------------------------------------------------------------------------------------------

def most_common( a ):
    return max(set(a), key = a.count)

# -----------------------------------------------------------------------------------------------
#   A little eye candy.

def do_titles_popup( sg, titles, location ):
    txt = '\n'.join( titles )

    location[0] += 20
    location[1] += 20

    titles_element = sg.Multiline(
        default_text = txt,
        key='titles-element',
        font=("Helvetica", 10 ),
        text_color = '#000000',
        background_color = '#e0e0ff',
        justification='left',
        write_only = True,
        # auto_size_text = True,            # Doesn't work as expected
        size = (50, 5),                     # set fixed size instead
        pad=((5,5), (5,5)),
        auto_refresh = True,
        no_scrollbar = True,
        expand_x = False,
        border_width = 0,
        visible = True,
        )

    layout = [ [titles_element] ]

    titles_window = sg.Window( '-',
         return_keyboard_events=False,
         location = location,
         resizable=False,
         icon=BL_Icon,
         finalize = True,
         layout=layout,
         keep_on_top = True,
         no_titlebar = True,
         margins = (0, 0),
         background_color = '#e0e0ff',
        )

    # ------------------------------------------
    #   No EVENT Loop for titles popup window.

    return titles_window

# -----------------------------------------------------------------------------------------------
#   Class for managing in-memory index and index file.
#   Page number may arrive as int or str. Always convert to str here and keep as str in self.index.

#   self.index: { page: [[ page, sheet, title ], [page, sheet, title], ... ], page: [[], []...], ... }

class Index():
    def __init__( self, file ):
        self.index = {}
        self.index_file = file
        self.last_page = 1
        self.data_present = False

    # ----------------------------------------------------------------

    def set_classes( self, conf ):
        self.conf = conf

    # -----------------------------------------------------------
    #   add() is most common operation. Append to end of file instead of
    #       rewriting whole file.
    #   WRW 24 Apr 2022 - The cleanup here is for user input. It is already done for OCR input but
    #       keep it there so it appears in the Title display as will be saved.

    def add( self, sheet, page, title ):
        spage = str(page)
        title = title.replace( '\t', '' )   # Remove tabs in case they leak in from tabbing between elements
        title = title.replace( '\n', ' ' )  # Remove line breaks thought there should be none since newline creates event.
      # title = title.strip()               # Remove leading/trailing space
      # title = title.title()               # Convert to title case for consistency of user input with OCR
        title = fb_title_correction.do_correction( None, title )        # WRW 26 Apr 2022

        # ------------------------------------------------------------
        #   First, check if title already exists on page. This could happen if user goes back to review.
        #   Disallow it as possible source of confusion. Force explicit 'Update' or 'Delete'

        found = False
        if spage in self.index:
            items = self.index[ spage ]
            for item in items:
                otitle = item[2]
                if otitle == title:
                    found = True
        if found:
            self.conf.do_popup( """The title you are saving already exists on that page.
Please use 'Update' to change it or 'Delete' to remove it.""" )
            return

        # ------------------------------------------------------------

        sheet = sheet.replace( '\t', '' )    # Likewise clean up sheet, just in case
        sheet = sheet.replace( '\n', '' )
        sheet = sheet.strip()

        self.index.setdefault( spage, [] ).append( [ spage, sheet, title ] )  # can have multiple titles on sheet

        with open( self.index_file, "a+", newline='' ) as ofd:        # newline='': no newline translation
            with io.StringIO() as csvfile:
                writer = csv.writer( csvfile, lineterminator='\n' )
                row = [title, page, sheet]                  # *** line format ***
                writer.writerow(row)
                print( csvfile.getvalue(), file=ofd, end='' )

        if int(page) > int(self.last_page):
            self.last_page = spage

        self.data_present = True

    # ----------------------------------------------------------------
    def has( self, page ):
        if not page:
            return None
        spage = str(page)
        return True if spage in self.index else False

    def has_data( self ):
        return self.data_present

    # ----------------------------------------------------------------
    def get_items( self, page ):
        if not page:
            return None

        spage = str(page)
        return self.index[ spage ] if spage in self.index else None

    # ----------------------------------------------------------------
    def get_titles( self, page ):
        if not page:
            return None

        spage = str(page)
        if spage not in self.index:
            return None

        items = self.index[ spage ] 
        titles = [ x[2] for x in items ]
        return titles

    # ----------------------------------------------------------------
    def get_last_page( self ):
        return self.last_page

    # ----------------------------------------------------------------
    def delete( self, page, title ):
        if not page:
            return     

        spage = str(page)
        if spage not in self.index:
            return     

        items = self.index[ spage ]
        nitems = []
        found = False
        for item in items:
            otitle = item[2]
            if otitle == title:
                found = True
            else:
                nitems.append( item )

        if found:
            self.index.pop( spage )             # Remove old item
            if nitems:
                self.index[ spage ] = nitems    # Add items with item removed only if any left.
            self.write()                        # And save to file.

        return

    # ----------------------------------------------------------------

    def update( self, page, title, ntitle ):
        if not page:
            return     

        spage = str(page)
        if spage not in self.index:
            return     

        items = self.index[ spage ]
        nitems = []
        found = False
        for item in items:
            otitle = item[2]
            if otitle == title:
                nitem = item
                nitem[2] = ntitle                    # Update title
                nitems.append( nitem )
                found = True
            else:
                nitems.append( item )

        if found:
            self.index.pop( spage )         # Remove old item
            self.index[ spage ] = nitems    # Add updated item
            self.write()                    # And save to file.

        return

    # ----------------------------------------------------------------
    #   Write self.index to index file

    def write( self ):
        with open( self.index_file, 'w', newline='' ) as ofd:
            csvwriter = csv.writer( ofd )
            for page in self.index:
                items = self.index[ page ]
                for item in items:
                    csvwriter.writerow( [ item[2], item[0], item[1] ] )

    # ----------------------------------------------------------------
    #   Read index file into self.index

    def read( self ):
        self.last_page = 0
        self.index = {}
        self.data_present = True

        with open( self.index_file, "r", newline='' ) as fd:
            reader = csv.reader( fd )
            for row in reader:
                if row:
                    title = row[0]
                    page  = row[1]
                    sheet = row[2]

                    self.index.setdefault( str(page), [] ).append( [ str(page), sheet, title ] )  # can have multiple titles on sheet

                    if int(page) > int(self.last_page):
                        self.last_page = page
                        self.last_title = title
                        self.last_sheet = sheet

# --------------------------------------------------------------
#   Goal here is to confine all knowledge of display elements to this class.

class Display():
    def __init__( self ):
        self.current_title = None
        self.index = None
        pass

    # -----------------------------------------------------------

    def process_events( self, event, values ):
        if event == 'create-index-review-table':
            index = values[ 'create-index-review-table' ][0]

            if self.review_table_data:
                title = self.review_table_data[ index ][2]
                self.ele_title.update( title )
                self.current_title = title
            else:
                self.ele_title.update( '' )
                self.current_title = None

            return True         # Is our event

        return False            # Not our event

    # -----------------------------------------------------------

    def page( self, page ):
        spage = str( page )
        self.ele_page.update( spage )

        if not self.index:
            return

        if self.index.has( spage ):
            items = self.index.get_items( spage )

            title = items[0][2]
            self.ele_title.update( title, text_color = '#ffffff' )
            self.current_title = title

            sheet = items[0][1]
            self.ele_sheet.update( sheet )

            self.fb.safe_update( self.ele_review_table, items )
            self.review_table_data = items

        else:
            self.ele_title.update( '' )
            self.current_title = None
            self.ele_sheet.update( '' )
            self.fb.safe_update( self.ele_review_table, [['','','']] )
            self.review_table_data = None

    # -----------------------------------------------------------

    def update_sheet( self, sheet ):
        self.ele_sheet.update( sheet )

    # -----------------------------------------------------------

    def update_title( self, title, text_color='#ffffff' ):
        self.ele_title.update( title, text_color=text_color )
        self.current_title = title

    # -----------------------------------------------------------

    def set_elements( self, title, sheet, page, review ):
        self.ele_title = title
        self.ele_sheet = sheet
        self.ele_page = page
        self.ele_review_table = review

    # -----------------------------------------------------------

    def set_classes( self, fb ):
        self.fb = fb

    # -----------------------------------------------------------
    #   I really have to start using inheritance but this is more obvious and understandable.

    def set_index( self, index ):
        self.index = index

    # -----------------------------------------------------------
    def get_current_title( self ):
        return self.current_title  

# ---------------------------------------------------------------------------------------------------------
#   WRW 26 Apr 2022 - Finally! Hit need to use inheritance.

# class Create( fb_pdf.PDF ):
class Create():

    # --------------------------------------------------------------
    def __init__( self ):
        self.src = None
        self.canonical = None
        self.table_loaded = False
        self.pdf_window = None
        self.box = None
        self.current_page = 1
        self.mag_window = None
        self.mag_figure = None
        self.mouse_state = 'Up'
        self.mag_size = 100             # Actual size is mag_size * zoom
        self.mag_zoom = 2               # Magnification of page, not graph
        self.index = None
        self.start_drag = None
        self.end_drag = None
        self.last_page = None
        self.page_size = None
      # self.review_table_data = None
        self.page_count = None

        self.pdf_shown = False
        self.display = Display()
        self.titles_window = None
        self.current_fig = None
        self.drawing_box = False

    # --------------------------------------------------------------

    def set_window( self, window ):
        self.window = window

    # --------------------------------------------------------------
    # def set_elements( self, dc, canonical, title, sheet, page, graph, canonical_table, main_frame, review_frame, review_table ):
    # def set_elements( self, dc, title, sheet, page, graph, canonical_table, main_frame, review_frame, review_table ):

    def set_elements( self, dc, title, sheet, page, graph, canonical_table, main_frame, review_table, sheet_label ):
        self.dc = dc
        self.ele_title = title
        self.ele_sheet = sheet
        self.ele_page = page
        self.ele_graph = graph
        self.ele_canonical_table = canonical_table
        self.ele_main_frame = main_frame
        self.ele_review_table = review_table
        self.ele_sheet_label = sheet_label

        self.display.set_elements( self.ele_title, self.ele_sheet, self.ele_page, self.ele_review_table )

    # -----------------------------------

    def set_classes( self, conf, sg, fb ):
        self.conf = conf                 
        self.sg = sg                     
        self.fb = fb                     

        self.display.set_classes( fb )

    # -----------------------------------
    #   See: https://www.tcl.tk/man/tcl8.6/TkCmd/keysyms.html
    #     int(ele_graph.user_bind_event.delta/120).

    def do_bind( self ):
      # self.ele_graph.bind( '<Enter>', '-Enter' )
      # self.ele_graph.bind( '<Leave>', '-Leave' )
      # self.ele_graph.bind( '<Motion>', '-Motion' )
      # self.ele_graph.bind( '<Shift-Motion>', '-Shift-Motion' )

        self.ele_graph.bind( '<Configure>', '-Config-Event' )    # size of widget changed

        self.ele_graph.bind( '<Button-1>',          '-Left-Click' )
        self.ele_graph.bind( '<B1-Motion>',         '-Left-Motion' )
        self.ele_graph.bind( '<ButtonRelease-1>',   '-Left-Click-Release' )

        self.ele_graph.bind( '<Button-3>',          '-Right-Click' )
        self.ele_graph.bind( '<B3-Motion>',         '-Right-Motion' )
        self.ele_graph.bind( '<ButtonRelease-3>',   '-Right-Click-Release' )

        self.ele_graph.bind( '<Left>',  '-Left' )   # Just these for synchronized navigation
        self.ele_graph.bind( '<Right>', '-Right' )
        self.ele_graph.bind( '<Up>',    '-Up' )
        self.ele_graph.bind( '<Down>',  '-Down' )

        if False:
            self.ele_graph.bind( '<Home>',  '-Home' )
            self.ele_graph.bind( '<End>',   '-End' )

      # self.ele_graph.bind( '<MouseWheel>',   '-MouseWheel' )              # Doesn't work on Graph() element
      # self.ele_graph.bind( '<Shift-MouseWheel>',   '-Shift-MouseWheel' )  # Doesn't work on Graph() element

        self.ele_page.bind(  '<Return>', '-Return' )        # Finally, got it to work. <Return> is the answer.

        self.ele_title.bind( '<Return>', '-Return' )
        self.ele_title.bind( '<Tab>', '-Tab' )

        self.ele_sheet.bind( '<Return>', '-Return' )
        self.ele_sheet.bind( '<Tab>', '-Tab' )

        #   At first glance I don't like this. Needs to be bound to Title and Sheet, too, but I'm afraid of confusion with that.
        # self.ele_graph.bind( '<KP_End>', '-Key-End' )           # These are 1, 2, 3 keys on the numerical keypad
        # self.ele_graph.bind( '<KP_Down>', '-Key-Down' )         # Experimental to see if adds usability.
        # self.ele_graph.bind( '<KP_Next>', '-Key-Next' )

    # -----------------------------------
    #   This done after set_classes() and set_window() called.

    def late_init( self ):
        self.pdf = fb_pdf.PDF()     # Create a new instance, will prevent any interaction
        self.pdf.set_classes( self.conf )
        self.pdf.set_class_config( )
        self.pdf.set_window( self.window )
      # self.pdf.set_graph_element( self.ele_graph, None )
        self.pdf.set_graph_element( self.ele_graph )
        self.pdf.do_bind()              # After set_graph_element()
        self.pdf.set_for( "Create Index" )   # A little debugging help.

      # self.pdf.register_page_change( 'ci-hidden-page-change' )            # Nope, got in the way.
      # self.pdf.set_fit( 'Both' )  # This is now the default in fb_pdf.py

    # -----------------------------------

    def set_icon( self, t ):
        global BL_Icon
        BL_Icon = t

    # -----------------------------------------------------------------------------------------------
    #   Populate the canonical table. Can't do this at init as don't have self.fb yet.

    def load_tables( self ):
        if self.table_loaded:
            return
        self.table_loaded = True

        # -----------------------------------------
        #   WRW 24 Apr 2022 - Finally add some sensible canonical selection.

        t = self.conf.val( 'ci_canon_select' )
        if t == 'All':
            self.canonicals = self.fb.get_canonicals_for_create( 'All' )

        elif t == 'With No Index':
            self.canonicals = self.fb.get_canonicals_for_create( 'No-Index' )

        elif t == 'Only With Index':
            self.canonicals = self.fb.get_canonicals_for_create( 'Only-Index' )

        else:
            print( f"ERROR-DEV: Unexpected value for 'ci_canon_select' option: '{t}'", file=sys.stderr )
            sys.exit(1)

        # -----------------------------------------

        self.fb.safe_update( self.ele_canonical_table, self.canonicals )

        path = self.fb.get_create_quick_ref()
        self.pdf.show_music_file_internal( path, 1 )        # Show quick-start file at startup
        self.page_size = self.pdf.get_current_page_size()
        self.pdf_shown = True

    # ---------------------------------------------------------------------------------------------------------
    def set_class_config( self ):
        pass

    # ---------------------------------------------------------------------------------------------------------
    #   Create a new window containing just a Graph element for the magnified image.

    def do_magnifier_prep( self ):

        size = self.mag_size * self.mag_zoom
        mag_graph = \
            self.sg.Graph( ( size, size ),
                key = 'mag-graph',
                graph_bottom_left=(0, size),
                graph_top_right=(size, 0),
                pad=((0,0),(0,0)),
            )

        layout = [[ mag_graph ]]

        self.mag_window = self.sg.Window( '-',
             return_keyboard_events=False,
             resizable=True,
             icon=BL_Icon,
             finalize = True,
             layout=layout,
             keep_on_top = True,
             no_titlebar = True,
             margins = (0, 0),
             # background_color = '#e0e0ff',
            )

    # -------------------------------------------------
    #   Show an image in the window created above.

    def do_magnifier( self, pixmap ):
        if self.mag_figure:                        # First delete the old one if it exists.
              self.mag_window[ 'mag-graph' ].delete_figure( self.mag_figure )

        self.mag_figure = self.mag_window[ 'mag-graph' ].draw_image( data = pixmap.tobytes(), location = (0, 0) )

    # ---------------------------------------------------------------------------------------------------------
    #   Argument 'box' is the 'figure' returned from drawing the outline around the text with draw_rectangle()
    #       I.e.: self.box = self.ele_graph.draw_rectangle()

    def get_text_from_box( self, box ):
        import pytesseract                              # Only import it when we need it.
        if box:

            # --------------------------
            #   Restrict select rectangle to just pdf page.
            #   Reminder:
            #       bb: ((tl_x, tl_y), (lr_x, lr_y))
            #       page_size: (width, height)              # in graph coordinates

            bb  = self.ele_graph.get_bounding_box( box )
            nbb = [ [ None for y in range( 2 ) ] for x in range( 2 ) ]

            nbb[0][0] = max( 0, bb[0][0] )
            nbb[0][0] = min( bb[0][0], self.page_size[0] )
            nbb[1][0] = max( 0, bb[1][0] )
            nbb[1][0] = min( bb[1][0], self.page_size[0] )

            nbb[0][1] = max( 0, self.page_size[1] )
            nbb[0][1] = min( bb[0][1], self.page_size[1] )
            nbb[1][1] = max( 0, bb[1][1] )
            nbb[1][1] = min( bb[1][1], self.page_size[1] )

            # --------------------------
            #   get_pixmap_from_bb() calling:
            #       dlist.get_pixmap( colorspace=fitz.csGRAY, alpha=False, matrix=zoom_matrix, clip=nbb )
            #       dlist.get_pixmap( colorspace=fitz.csGRAY, alpha=False, dpi=300, clip=nbb )

            pixmap = self.pdf.get_pixmap_from_bb( nbb )

            # --------------------------

            #   /// RESUME OK - Any benefit to apply some OCR pre-processing to image?

            # --------------------------
            #   This was helpful to see what part of the page was actually selected.

            Testing = False
            if Testing:
                if self.pdf.pdf_figure:     # Delete current image            # Just for testing
                     self.pdf.graph_element.delete_figure( self.pdf.pdf_figure )

                image = pixmap.tobytes()    #   Note, pixmap.tobytes() defaults to output='png'
                self.pdf.graph_element.draw_image( data = image, location = (10, 10) )     # just testing
            # --------------------------

            bytes = pixmap.pil_tobytes( format='png' )                  # Convert pixmap to png bytes
            Path( "/tmp/t.png" ).write_bytes( bytes )                   # Save image in file for conversion to title
          # title = pytesseract.image_to_string( bytes )                # /// RESUME OK - get this to work without intermediate file.
            title = pytesseract.image_to_string( "/tmp/t.png" )         # Convert image to text
          # title = title.strip()                                       # Remove leading/trailing space
            title = title.replace( '\n', ' ' )                          # Remove newline
          # title = title.title()                                       # Convert to title case
            title = fb_title_correction.do_correction( None, title )    # WRW 26 Apr 2022
            return title

        else:
            return ''

    # ---------------------------------------------------------------------------------------------------------
    #   /// RESUME - can't get focus to Graph(), bind() issues? Go back to processing keystrokes?
    #       or remove support for mouse wheel

    def process_events( self, event, values ):

        # self.ele_canonical_table.Widget.config(takefocus=0)     # /// RESUME WRW 26 Apr 2022 - Experimental

        # print( "/// ci event: ", event )
        # focus = self.window.find_element_with_focus()
        # print( "   ci focus:", focus )
        # print( "/// values:", values )

        # -------------------------------------------

        if values[ 'ci-auto-ocr-switch' ]:
            auto_ocr = True                                 # A convenience variable
        else:
            auto_ocr = False

        if values[ 'ci-title-number-switch' ]:
            use_title_numbers = True                        # A convenience variable
            self.ele_sheet_label.update( 'Title #:' )
        else:
            use_title_numbers = False
            self.ele_sheet_label.update( 'Sheet #:' )

        # -------------------------------------------
        #   A big reminder: self.pdf is the sg.Graph() element for the pdf display in the Create Index tab.
        #   WRW 27 Apr 2022 - Don't let pdf process events for create.

        # if self.pdf.process_events( event, values ):
        #     return True

        # -------------------------------------------
        #   Now processing display class events in class, not here.

        if self.display.process_events( event, values ):
            return True

        # -------------------------------------------

      # elif event == 'ele_graph-pdf-Left' or event == 'ele_graph-pdf-Up':
      # elif event == 'create-index-graph-Left':
      #     self.pdf.prev_page()
      #     return True

      # elif event == 'ele_graph-pdf-Right' or event == 'ele_graph-pdf-Down':
      # elif event == 'create-index-graph-Right':
      #     self.pdf.next_page()
      #     return True

      # elif event == 'ele_graph-pdf-Home':
      #     self.pdf.first_page()
      #     return True

      # elif event == 'ele_graph-pdf-End':
      #     self.pdf.last_page()
      #     return True

        # -------------------------------------------

        elif event == 'create-index-title-Tab':
            self.ele_sheet.set_focus()
            return True

        elif event == 'create-index-sheet-Tab':
            self.ele_title.set_focus()
            return True

        # -------------------------------------------
        #   WRW - 26 Apr 2022
        #   Hmmm. Things getting a little messy. Want this event when changing pages
        #       external to the controls here, i.e., via keyboard or mousewheel controls,
        #       not when we do it here because it will result in a blank title and sheet.
        #       Disable it for now. /// RESUME - add blocking flag set when we update here?
        #       Perhaps only send it from fb_pdf() for internally generated changes? That looks OK.
        #       No, no, no. That would conflice with meta needs. Don't use it at all

      # elif event == 'ci-hidden-page-change':
      #     page = self.pdf.get_cur_page()                                                                                
      #   # self.display.page( page )

        # -------------------------------------------
        #   Click in canonical table. Load the PDF file indicated by the canonical name.

        #   Reminder: self.canonicals is nested array, i.e., array of arrays,        
        #       so we can update canonical table directly with it.
        #       Update requires array of rows and each row is array of values. Using just one value/row here.

        elif event == 'create-index-canonical-table':
            self.canonical = self.canonicals[ values[ 'create-index-canonical-table' ][0] ][0]

            # ------------------------------------------------------------
            #   Display music file in PDF graph.                                                  

            music_file = self.fb.get_file_from_canonical( self.canonical )

            if not music_file:            # Nothing to do if no music file for canonical book name
                self.conf.do_popup( f"No music file associated with canonical {self.canonical}" )
                return True         

            path = Path( self.fb.Music_File_Root, music_file )
            self.pdf.show_music_file_internal( path, self.current_page )        # *** Show PDF file.
            self.page_size = self.pdf.get_current_page_size()
            self.page_count = self.pdf.page_count
            self.pdf_shown = True

            # ------------------------------------------------------------
            #   Load or initialize index
            #   WRW 7 May 2022 - Add 'Raw-Index'

            index_file = Path( self.conf.get_source_path( "User" ), 'Raw-Index', self.canonical + ".csv" )

            self.index = Index( index_file )                    # This just saves name, no access yet.
            self.display.set_index( self.index )
            self.index.set_classes( self.conf )

            # if not index_file.exists():
            #     self.display.page( 0 )

            if index_file.exists():
                self.index.read()
                self.last_page = self.index.get_last_page()

                if self.last_page:                                  # Will not have last_page if don't have index yet.
                    self.pdf.goto_page( int(self.last_page) )

            page = self.pdf.get_cur_page()      # Always work from fb_pdf.py page number for consistency if limits applied
            self.display.page( page )

            return True

        # -------------------------------------------
        #   *** Click on 'Save' or 'Save+' button ***
        #       WRW 24 Apr 2022 - or Return in Title or Sheet. Treat it as 'Save+' as that is most common.

        elif( event == 'create-index-save' or 
              event == 'create-index-save-plus' or
              event == 'create-index-title-Return' or
              event == 'create-index-sheet-Return' ):
           #  event == 'create-index-graph-Key-End' ):

            if( event == 'create-index-save-plus' or
                event == 'create-index-title-Return' or
                event == 'create-index-sheet-Return'  ):
            #   event == 'create-index-graph-Key-End' ):
                  auto_advance = True
            else:
                  auto_advance = False

          # auto_advance = True if event == 'create-index-save-plus' else False

            title = values[ 'create-index-title' ]
            sheet = values[ 'create-index-sheet' ]
            page = values[ 'create-index-page' ]

            # -------------------------------
            if not title:
                self.conf.do_popup( "Please enter a title before saving" )
                return True

            if not sheet:
                self.conf.do_popup( "Please enter a sheet number before saving" )
                return True

            # -------------------------------
            #   Add to internal database and index file

            self.index.add( sheet, page, title )

            # -----------------------------------------
            #   Possibly advance to the next page

            if auto_advance:
                self.pdf.next_page()                    # Go to the next page
                page = self.pdf.get_cur_page()
                self.display.page( page )

                sheet = int( sheet ) + 1
                self.display.update_sheet( sheet )          # Propose the next sheet number

            else:
                self.display.page( page )               # Update display for current page.

            # -----------------------------------------
            #   Possibly do OCR on title on next page. This works great when pages have
            #       titles in the same place and no extraneous noise around the title like staff lines.
            #       Otherwise, user will redraw the select box.
            #   Don't do it if not auto_advance as title will definitely be in another location.

            if auto_ocr and auto_advance:
                title = self.get_text_from_box( self.box )      # Get next title from old box.
                self.display.update_title( title, Auto_OCR_Save_Color )   # Draw title in green if from auto_ocr

                if self.start_drag and self.end_drag:
                    self.box = self.ele_graph.draw_rectangle(
                        self.start_drag,
                        self.end_drag,
                        line_color = Auto_OCR_Save_Color,     # Re-draw rectangle at prior location but in green
                        line_width = 2,
                    )
            else:
                self.display.update_title( '', '#ffffff' )

            # -----------------------------------------

            self.ele_title.set_focus()              # In case we are tabbing between elements get back to the title.
            return True

        # -------------------------------------------
        #   Click on 'Goto" button to go to a specific page entered in page input box

        elif event == 'create-index-goto' or event == 'create-index-page-Return':
            try:
                page = int( values[ 'create-index-page' ] )
            except:
                self.conf.do_popup( "Page must be numeric" )
                return True

            self.pdf.goto_page( page )                      # Limits to pages in book.
            page = self.pdf.get_cur_page()
            self.display.page( page )

            return True

        # -------------------------------------------
        #   Click on Prev                 

        elif( event == 'create-index-prev' or 
              event == 'create-index-graph-Up' or
              event == 'create-index-graph-Left' ):

            limit = self.pdf.prev_page()                    # prev_page() does the decrementing and limit work.
            page = self.pdf.get_cur_page()
            self.display.page( page )

            # -------------------------------------------
            #   If new page is not in the index update the sheet number on prev if there already is one.
            #       If there is not one we don't know the value to decrement. If it is in the index
            #       then that value has already been displayed by display.page()

            if self.index and not self.index.has( page ):
                if not limit:
                    sheet = values[ 'create-index-sheet' ]                                                      
                    if sheet:
                        sheet = int( sheet ) - 1
                        self.display.update_sheet( sheet )

                    # -------------------------------------------
                    #   Possibly recognize next title of Prev.
                    #   NO! I didn't like it.

                    if False and auto_ocr:
                        title = self.get_text_from_box( self.box )      # Get next title from old box.
                        self.display.update_title( title, Auto_OCR_Save_Color )

                        if self.start_drag and self.end_drag:           # Draw the select rectangle in distinct color
                            self.box = self.ele_graph.draw_rectangle(
                                self.start_drag,
                                self.end_drag,
                                line_color = Auto_OCR_Save_Color,
                                line_width = 2,
                            )

                    # -------------------------------------------

            return True

        # -------------------------------------------
        #   Click on Next or Skip
        #   WRW 24 Apr 2022 - Require sheet number to Skip and save with indicator for coverage map.
        #   WRW 8 May 2022 - Include considertion of title numbers vs sheet numbers.
        #       Don't demand a sheet number if using title numbers.

        elif( event == 'create-index-next' or 
              event == 'create-index-skip' or
              event == 'create-index-graph-Down' or
              event == 'create-index-graph-Right' ):

            if event == 'create-index-skip':
                skip_flag = True
                page = values[ 'create-index-page' ]

                if not use_title_numbers:
                    sheet = values[ 'create-index-sheet' ]
                    if not sheet:
                        self.conf.do_popup( "Please enter a sheet number before skipping" )
                        return True
                else:
                    sheet = ''

                self.index.add( sheet, page, '--Skip--' )          # Add an indicator that we have skipped the page for the coverage map.
            else:
                skip_flag = False

            # -------------------------------------------

            limit = self.pdf.next_page()                    # Does the decrementing and limit work
            page = self.pdf.get_cur_page()
            self.display.page( page )

            # -------------------------------------------
            #   If new page is not in the index update the sheet number on Next/Skip if there already is one.
            #       If there is not one we don't know the value to increment. If it is in the index
            #       then that value has already been displayed by display.page()
            #   WRW 8 May 2022 - Include considertion of title numbers vs sheet numbers.
            #       Don't update title number if using title numbers.

            if self.index and not self.index.has( page ):
                if not limit:

                    sheet = values[ 'create-index-sheet' ]  # Also update sheet on next, too, if already defined
                    if sheet:
                        if not use_title_numbers:
                            sheet = int( sheet ) + 1
                        self.display.update_sheet( sheet )

                    # -------------------------------------
                    #   Possibly automatically recognize next title on Skip, not on Next.

                    if skip_flag and auto_ocr and event == 'create-index-skip':
                        title = self.get_text_from_box( self.box )      # Get next title from old box.
                        self.display.update_title( title, Auto_OCR_Skip_Color )

                        if self.start_drag and self.end_drag:           # Draw the select rectangle in distinct color
                            self.box = self.ele_graph.draw_rectangle(
                                self.start_drag,
                                self.end_drag,
                                line_color = Auto_OCR_Skip_Color,
                                line_width = 1,
                            )

                    # -------------------------------------

            return True

        # -------------------------------------------
        #   Click on 'Last Created' button
        #   Set page to the highest numberd page saved.

        elif event == 'create-index-last-created':
            if self.last_page:
                self.pdf.goto_page( int(self.last_page) )
                page = self.pdf.get_cur_page()
                self.display.page( page )

            return True

        # -------------------------------------------
        #   Mouse down and drag in graph. May outside of graph.
        #   Display magnified view of PDF under mouse. Mainly for reading small sheet numbers.

        #   Top left is 0,0

        elif event == 'create-index-graph-Right-Click' or event == 'create-index-graph-Right-Motion':
            self.ele_graph.set_focus()                      # /// RESUME - Experimental

            if not self.pdf_shown:
                return True

            if self.mouse_state == 'Up':
                self.do_magnifier_prep()
            self.mouse_state = 'Down'

            mx, my = values[ 'create-index-graph' ]     # Click at mx, my in graph coordinates, i.e., pixels

            #   Move window created at do_magnifier_prep() to follow cursor
            gx = self.ele_graph.Widget.winfo_rootx()    # Get 0,0 of graph element
            gy = self.ele_graph.Widget.winfo_rooty()
            size = self.mag_size * self.mag_zoom
            self.mag_window.move( gx + mx - int(size/2),       # Position top-left corner
                                  gy + my - int(size/2) )

            pixmap = self.pdf.get_magnified_pixmap( mx, my, self.mag_size, self.mag_zoom )   # get_image_at_point() will limit to image bounds.
            self.do_magnifier( pixmap )

            return True

        # -------------------------------------------
        #   Mouse up, remove magnifier.

        elif event == 'create-index-graph-Right-Click-Release':
            self.mouse_state = 'Up'
            if self.mag_window:
                self.mag_window.close()
            return True

        # -------------------------------------------
        #   Resize main window.

        elif event == 'create-index-graph-Config-Event':
            if( values[ "main-tabgroup" ] == 'tab-mgmt-subtabs' and
                values[ 'index-mgmt-tabgroup' ] == 'tab-create-index' and
                self.pdf_shown
                ):

                self.pdf.refresh()
            return True

        # -------------------------------------------
        #   Adding OCR, see:
        #       See: https://towardsdatascience.com/optical-character-recognition-ocr-with-less-than-12-lines-of-code-using-python-48404218cccb
        #   May need export TESSDATA_PREFIX=/usr/share/tessdata to use some tools, not for this.

        #   Mouse click, start selection box.
        #   WRW 24 Apr 2022 - Add simple state machine so don't try to do OCR on motion after click in coverage map.

        elif event == 'create-index-graph-Left-Click':
            self.ele_graph.set_focus()                      # /// RESUME - Experimental

            mx, my = values[ 'create-index-graph' ]                                                   
            self.start_drag = [mx, my]
            self.drawing_box = True
            return True

        # -------------------------------------------
        #   Mouse drag, enlarge selection box.
        #   Peculiar situation here when click in map. Map is closed, a new page is shown, but
        #       we get a Left-Motion event yielding end_drag without a corresponding start_drag.
        #       self.box is graph feature identifier returned by draw_rectangle() below.

        elif event == 'create-index-graph-Left-Motion':
            if not self.drawing_box:                        # Ignore if mouse not clicked in pdf graph.
                return True

            mx, my = values[ 'create-index-graph' ]                                                   
            self.end_drag = [ mx, my ]

            if self.box:
                self.ele_graph.delete_figure( self.box )

            if self.start_drag and self.end_drag:           # See note above.
                self.box = self.ele_graph.draw_rectangle(   # Draw the select rectangle in distinct color
                    self.start_drag,
                    self.end_drag,
                    line_color = Manual_OCR_Color,
                    line_width = 1,
                )
            return True

        # -------------------------------------------
        #   Mouse up, extract text within selection box.

        elif event == 'create-index-graph-Left-Click-Release':
            if not self.drawing_box:                        # Ignore if mouse not clicked in pdf graph.
                return True
            self.drawing_box = False

            title = self.get_text_from_box( self.box )
            self.display.update_title( title, Manual_OCR_Color )     # Try drawing text in red, same as user-drawn selection box

          # self.ele_graph.delete_figure( self.box )          # Better to leave select box on screen so can see what we selected.
            return True

        # -------------------------------------------
        #   WRW 20 Apr 2022 - For experimentent with extracting text from PDF.
        #       No text in any fakebook I tried. Leave code here but 'Ex' button in gui commented out.

        elif event == 'create-index-experiment':
            text = self.pdf.get_text( self.current_page )

            if False:           # for 'blocks'
                res = []
                for block in text:
                    res.append( block[4] )
                text = '\n'.join( res )

            self.conf.do_popup( text )
            return True

        # -------------------------------------------
        elif event == 'create-index-delete':
            title = values[ 'create-index-title' ]
            page = values[ 'create-index-page' ]

            if self.index:
                self.index.delete( page, title )
                self.display.page( page )
            return True

        # -------------------------------------------
        elif event == 'create-index-update':
            ntitle = values[ 'create-index-title' ]
            page = values[ 'create-index-page' ]

            otitle = self.display.get_current_title()

            if self.index:
                self.index.update( page, otitle, ntitle )
                self.display.page( page )
            return True

        # -----------------------------------------------------------------------------------------------
        #   Show a map of pages already labeled.

        elif event == 'create-index-show-map':

            if not self.index or self.index and not self.index.has_data():      # Nothing to draw
                self.conf.do_popup( "No index data created for selected book." )
                return True

            boxes_h = 50
            boxes_v = 20
            boxes_v = int(self.page_count / boxes_h) + 1
            box_gap = 6
            box_size = 12

            box_line_width = boxes_h * (box_size + box_gap ) - box_gap
            box_line_height = boxes_v * (box_size + box_gap ) - box_gap

            border_size = 10
            text_area_y_axis   = 40
            text_area_x_axis   = 20
            graph_size_x  = box_line_width  + 2*border_size + text_area_y_axis
            graph_size_y  = box_line_height + 2*border_size + text_area_x_axis
            fig_map = {}

            canonical_text = self.sg.Text( self.canonical, pad=((10,10),(10,0)), font=("Helvetica", 14 ), text_color='#ffffff', justification='left', expand_x = True ),

            map_graph = self.sg.Graph( (graph_size_x, graph_size_y),
                key = 'map-graph',
                graph_bottom_left=(0, graph_size_y),
                graph_top_right=(graph_size_x, 0),
              # background_color = 'red',
                pad=((10,0),(10,0)),
                expand_x = True,
                expand_y = True,
                enable_events = True,                                                   
                motion_events = False,          # Didn't get motion when True.
            )

            txt = """Green box: title saved.
Blue box: page skipped.
Red box: title not saved or page not skipped.
Click in square to go to page.
Number of titles on page shown in box. """
            map_text = self.sg.Text( txt, pad=((10,10),(10,0)), font=("Helvetica", 10 ), text_color='#ffffff', justification='left', expand_x = True ),

            map_ok_button = self.sg.Button('OK', key='map-ok-button', font=("Helvetica", 9), pad=((10,0),(10,10)), expand_x = False  )

            map_layout = [
                            [ canonical_text ],
                            [ map_graph ],
                            [ map_text ],
                            [ map_ok_button],
                         ]

            map_window = self.sg.Window( 'Index Coverage Map by Page Number',
                 return_keyboard_events=False,
                 resizable=False,
                 icon=BL_Icon,
                 finalize = True,
                 layout=map_layout,
                 keep_on_top = True,
                )

            map = map_window[ 'map-graph' ]         # Convenience variable

            map.bind( '<Motion>', '-Motion' )       # this does work

            # --------------------------------------------------
            #   Y-Axis labels
            #   Draw page numbers on left side of graph

            for yi in range( 0, boxes_v ):
                y = yi % boxes_h
                ry = y * ( box_size + box_gap ) + border_size + text_area_x_axis + 8

                pgy = str(( y * boxes_h ) + 1 )

                map.draw_text( pgy,
                    ( text_area_y_axis, ry ),
                    color = "white",
                    font=("Helvetica", 9),
                    angle = 0,
                    text_location = self.sg.TEXT_LOCATION_RIGHT,
                )

            # --------------------------------------------------
            #   X-Axis labels
            #   Draw page numbers on top of graph

            for xi in range( 0, boxes_h ):
                x = xi          
                rx = x * ( box_size + box_gap ) + border_size + text_area_y_axis + 4

                pgx = str( x  + 1 )

                map.draw_text( pgx,
                    ( rx, text_area_x_axis ),
                    color = "white",
                    font=("Helvetica", 9),
                    angle = 270,
                    text_location = self.sg.TEXT_LOCATION_RIGHT,
                )

            # --------------------------------------------------
            #   Draw one box per page in book.

            exit_flag = False
            for yi in range( 0, boxes_v ):
                if exit_flag:
                    break

                for xi in range( 0, boxes_h ):
                    x = xi % boxes_h
                    y = yi % boxes_v

                    page = x + y * boxes_h + 1
                    if page > self.page_count:
                        exit_flag = True
                        break

                    if self.index.has( page ):
                        items = self.index.get_items( page )
                        title = items[0][2]
                        if title == '--Skip--':
                            title_count = None
                            color = '#0000ff'                       # Blue if skipped

                        else:
                            title_count = str( len( items ) )
                            color = '#00ff00'                       # Green if title(s)

                    else:
                        color = '#c00000'                           # Red if not labeled
                        title_count = None

                    rx = x * ( box_size + box_gap ) + border_size + text_area_y_axis
                    ry = y * ( box_size + box_gap ) + border_size + text_area_x_axis

                    top_left = (rx,ry)
                    bottom_right = (rx + box_size, ry + box_size )

                    fig = map.draw_rectangle(
                        top_left,
                        bottom_right,
                        fill_color = color,
                        line_color = color,
                        line_width = 1  
                    )
                    fig_map[ fig ] = page

                    # if self.index.has( page ):
                    #     items = self.index.get_items( page )
                    #     title_count = str( len( items ) )

                    if title_count:
                        map.draw_text( title_count,
                            (rx + int(box_size/2), ry+box_size -4 ),
                            color = "#000000",
                            font=("Helvetica", 9),
                            angle = 0,
                            text_location = self.sg.TEXT_LOCATION_CENTER,
                        )

            # ------------------------------------------
            #   EVENT Loop for map window

            while True:
                event, values = map_window.Read( )
                # print( "/// map event", event )

                # ------------------------------------------
                if event == self.sg.WINDOW_CLOSED:
                    break

                elif event == 'map-ok-button':
                    map_window.close()
                    break

                # ------------------------------------------
                elif event == 'map-graph+MOVE':                         # Not getting this, motion_events=True was set.
                    pass

                # ------------------------------------------
                elif event == 'map-graph-Motion':                                                                        

                    fig = map.get_figures_at_location( values[ 'map-graph' ] )

                    #   Don't redraw while on same square. Remember fig here may have two elements, the square and number.
                    if fig and self.current_fig and self.current_fig == fig[0]:
                        continue                                       # Continue event loop

                    if fig and fig[0] in fig_map:
                        self.current_fig = fig[0]
                        page = fig_map[ fig[0] ]
                        titles = self.index.get_titles( page )
                        if titles:
                            if self.titles_window:
                                self.titles_window.close()

                            mx = map.Widget.winfo_rootx() + values[ 'map-graph' ][0]
                            my = map.Widget.winfo_rooty() + values[ 'map-graph' ][1]
                            self.titles_window = do_titles_popup( self.sg, titles, [mx, my])
                    else:
                        if self.titles_window:
                            self.titles_window.close()
                            self.titles_window = None
                            self.current_fig = None

                # ------------------------------------------
                elif event == 'map-graph':
                    fig = map.get_figures_at_location( values[ 'map-graph' ] )
                    if fig and fig[0] in fig_map:
                        page = fig_map[ fig[0] ]  
                        if self.titles_window:
                            self.titles_window.close()

                        map_window.close()

                        self.pdf.goto_page( page )                      # Limits to pages in book.
                        page = self.pdf.get_cur_page()
                        self.display.page( page )

            # ------------------------------------------

            self.start_drag = None
            self.end_drag = None
            return True

        # -------------------------------------------
        #   Didn't recognize any of our events.

        return False

# -----------------------------------------------------------------------------------------------

