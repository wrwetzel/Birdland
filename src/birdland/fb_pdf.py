#!/usr/bin/python
# ---------------------------------------------------------------------------------------
#   fb_pdf.py 

#   WRW 21 Jan 2022 - module for displaying PDF files in Bluebird.
#   Code extracted from bluebird.py and refactored to isolate pdf-related logic.
#   Unlike earlier pdf code from fb_utils.py this module has knowledge of GUI.

#   Several ways to show pdf file:
#       Initial display of Help Doc
#       Show Help Doc from menu
#       Click in:
#           Setlist table
#           Indexed music file table
#           Music file table
#           Browse music file tree

#   Additional inputs:
#       Scroll up/down
#       Home, end, page up, page down
#       Zoom in/out
#       Fit full, vert, hori

#   File here is full path. Calling program adds root to any relative path.
#   Internal page numbers are 0-based, external (what the user sees) are 1-based.

#   WRW 26 Apr 2022 - Looks like I had some confusion between managing the 'Music Viewer' tab
#       and the PDF graph. This is common code that is use by 
#       PDF display in both 'Music Viewer' and 'Create/Edit Index'. That is refelecte in
#       the need for the fb_meta.py and hidden-page-change event.
#       /// RESUME OK - working fine now but I don't like the program structure. Later.

# ---------------------------------------------------------------------------------------

import os
import sys
import subprocess
import shutil
import fitz
from pathlib import Path

# ---------------------------------------------------------------------------------------

class PDF():

    # --------------------------------------------------------------
    def __init__( self ):
        self.doc = None
        self.image = None
        self.pdf_figure =  None
        self.zoom = 1
        self.zoom_set = False
        self.fit = 'Both'               # WRW 18 Apr 2022 - Added this to get fit in any aspect ratio.
        self.current_file = None
        self.page_count = None
        self.cur_page = 0

        self.current_pixmap_y = None               # Position of origin of pixmap relative to origin of graph, 0 or negative.
        self.mouse_start_pos =  None
        self.mouse_state = 'up'

        self.music_popen = None
        self.UseExternalMusicViewer = None

        self.external_viewer = False
        self.dlist = None
        self.page_change = None

    # --------------------------------------------------------------
    #   A little debugging help. for is text description of tab using pdf

    def set_for( self, txt ):
        self.for_txt = txt

    # --------------------------------------------------------------

    def set_classes( self, conf ):
        self.conf = conf

    # --------------------------------------------------------------
    #   See: https://www.tcl.tk/man/tcl8.6/TkCmd/keysyms.html
    #     int(graph_element.user_bind_event.delta/120).

    def do_bind( self ):
        self.graph_element.bind( '<Configure>', '-Config-Event' )    # size of widget changed

        if False:
            self.graph_element.bind( '<Left>',      '-Left' )
            self.graph_element.bind( '<Right>',     '-Right' )
            self.graph_element.bind( '<Up>',        '-Up' )
            self.graph_element.bind( '<Down>',      '-Down' )
            self.graph_element.bind( '<Home>',      '-Home' )
            self.graph_element.bind( '<End>',       '-End' )

    #   self.graph_element.bind( '<MouseWheel>',        '-MouseWheel' )             # Not working on graph element.
    #   self.graph_element.bind( '<Shift-MouseWheel>',  '-Shift-MouseWheel' )       # Not working.

    # --------------------------------------------------------------

    def set_class_config( self ):                  
        self.UseExternalMusicViewer =   self.conf.val( 'use_external_music_viewer' )
        self.ExternalMusicViewer    =   self.conf.val( 'external_music_viewer' )
        self.MusicFileRoot          =   self.conf.val( 'music_file_root' )

    # --------------------------------------------------------------
    def set_window( self, window ):      # PySimpleGui window
        self.window = window

    # --------------------------------------------------------------
    #   WRW 26 Apr 2022 - Made page change announcement selective. Only used when Pdf() created
    #       from birdland.py, not fb_create_index.py. Nope, added it there, too.

    def register_page_change( self, key ):
        self.page_change = key

    def report_page_change( self ):
        if self.page_change:
            self.window[ self.page_change ].click()     # tell others there is a new page

    # --------------------------------------------------------------
    #   WRW 18 Apr 2022 - graph_element can change, used for Music Viewer and Create Index.
    #   WRW 1 May 2022 - Finally got around to adding a slider to change page.

  # def set_graph_element( self, graph_element, slider_element ):      # PySimpleGui Graph element
    def set_graph_element( self, graph_element ):      # PySimpleGui Graph element
        self.graph_element = graph_element
      # self.slider_element = slider_element

    # --------------------------------------------------------------
    #   WRW 18 Apr 2022 - For Create Index work.

    def set_fit( self, fit ):
        self.fit = fit

    # --------------------------------------------------------------

    def close( self ):
        if self.doc:
            self.doc.close()

        if self.music_popen:
            self.music_popen.kill()

    def close_ext( self ):
        if self.music_popen:
            self.music_popen.kill()

    # --------------------------------------------------------------
    #   show_music_file() always uses internal Music Viewer or and external viewer.
    #   show_music_file_internal() uses whatever is set in self.graph_element.

    def show_music_file( self, file=None, page=None, force=None ):

        if force or not self.UseExternalMusicViewer:
            self.external_viewer = False
            self.show_music_file_internal( file=file, page=page )

        else:
            self.external_viewer = True
            self.show_music_file_external( file, page )

    # --------------------------------------------------------------

    def show_music_file_external( self, file, page ):

        fullpath = os.path.join( self.MusicFileRoot, file )
        viewer = self.ExternalMusicViewer    

        if not Path( fullpath ).is_file():                  # Likely excessive but let's be safe.
            t = f"Can't find music file '{fullpath}'."
            self.conf.do_popup( t )
            return

        if self.music_popen:
            self.music_popen.kill()

        if not viewer:
            t = f"No PDF Music Viewer given in config file"
            self.conf.do_popup( t )
            return

        if shutil.which( viewer ):
            if page:
                show_cmd = [ viewer, fullpath, '-p', page ]
            else:
                show_cmd = [ viewer, fullpath ]

            self.music_popen = subprocess.Popen( show_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

        else:
            t = f"PDF Music Viewer given in config file '{viewer}' not found."
            self.conf.do_popup( t )
            return

    # --------------------------------------------------------------
    #   Primary function of this module. If file not included just update page in current file.

    def show_music_file_internal( self, file=None, page=None ):
        self.cur_page = int( page ) - 1     # zero-based numbers internally

        if file:
            # self.graph_width, self.graph_height = self.graph_element.get_size()  # From size

            #   Cache file so don't have to reopen if new is the same as prior file.
            if file != self.current_file:

                # ----------------------------------------
                #   Close doc if already open.

                try:
                    if self.doc:
                        self.doc.close()
                        self.doc = None

                except Exception as e:
                    (extype, value, traceback) = sys.exc_info()
                    print( f"ERROR-DEV on self.doc.close(), type: {extype}, value: {value}", file=sys.stderr )
                    print( f"  {file}", file=sys.stderr  )
                    return None

                # ----------------------------------------
                #   Create new doc from file

                #   WRW 1 June 2022 - A little more checking to be safe.

                path = Path( file )
                if not path.is_file():
                    t = f"ERROR: PDF file {path.as_posix()} not found at show_music_file_internal()"
                    self.conf.do_popup( t )
                    return      

                self.doc = fitz.open( file )
                self.page_count = self.doc.page_count
                self.current_file = file

        # ----------------------------------------
        #   Delete prior figure in graph, if any.

        if self.pdf_figure:
             self.graph_element.delete_figure( self.pdf_figure )

        # ----------------------------------------
        #   A little initialization of mouse-movement parameters

        self.mouse_start_pos = None,
        self.mouse_state = 'up'
        self.current_pixmap_y = None                                                                                         

        # ----------------------------------------
        #   Get new image and draw it on graph

        zoom = self.get_zoom_from_fit()
        self.image = self.get_image( zoom, self.cur_page )

        if self.image:
            self.pdf_figure = self.graph_element.draw_image( data = self.image.tobytes(), location = (0, 0) )

        else:
            print( f"ERROR-DEV get_image() failed, cur_page: {self.cur_page}, zoom: {zoom}", file=sys.stderr )

    # --------------------------------------------------------------
    #   Refresh - Redraw image with new window size, zoom, or page.
    #   /// RESUME OK - Preserve location on page during zoom and resize.

    def refresh( self ):
        if self.external_viewer:
            return

        self.mouse_start_pos = None
        self.mouse_state = 'up'

        if self.pdf_figure:     # Delete current image
             self.graph_element.delete_figure( self.pdf_figure )

        zoom = self.get_zoom_from_fit()

        self.image = self.get_image( zoom, self.cur_page )
        if self.image:
            self.pdf_figure = self.graph_element.draw_image( data = self.image.tobytes(), location = (0, 0) )

        # t = self.graph_element.get_size()
        # print( "size:", t )
        # self.slider_element.set_size( size=(None, t[1]) )
        # self.slider_element.update( range = () )

    # --------------------------------------------------------------
    #   Get information about the current document

    def get_info( self ):
        return { 'page_count' : self.page_count, 
                 'page' : self.cur_page + 1,
                 'file' : self.current_file,
               }

    # --------------------------------------------------------------
    #   WRW 1 Feb 2022 - Need page count before PDF displayed. Here it is self contained.

    def get_page_count( self, file ):
        doc = fitz.open( file )
        page_count = doc.page_count
        doc.close()
        return page_count

    # --------------------------------------------------------------
    #   Get zoom factor from current graph size, not saved graph size, and page size.
    #   Save zoom setting in self.zoom.
    #   WRW 25 Mar 2022 - Pull out common code from elifs even though may not always be used.

    def get_zoom_from_fit( self ):
        if self.doc:
            if self.cur_page >= self.page_count:
                t = f"ERROR: Selected page {self.cur_page +1} exceeds document page count {self.page_count +1}"
                self.conf.do_popup( t )
                self.cur_page = self.page_count -1    # Fail gracefully with announcement

            graph_width, graph_height = self.graph_element.get_size()
            fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
            r = self.doc[self.cur_page].get_displaylist().rect
            fitz.TOOLS.mupdf_display_errors(True)
            self.page_height = (r.br - r.tr).y
            self.page_width =  (r.tr - r.tl).x

            if self.fit == 'Full':
                self.zoom = 1

            elif self.fit == 'Height':
                if self.cur_page < len(self.doc):
                    self.zoom = graph_height / self.page_height

            elif self.fit == 'Width':
                if self.cur_page < len(self.doc):
                    self.zoom = graph_width / self.page_width

            elif self.fit == 'Both':
                if self.cur_page < len(self.doc):
                    zoom_width = graph_width / self.page_width
                    zoom_height = graph_height / self.page_height
                    self.zoom = min( zoom_width, zoom_height )

            elif self.fit == 'User':        # After user adjusted zoom setting with +/-.
                return self.zoom

            else:
                self.zoom = 1

        return self.zoom
    
    # ---------------------------------------------------------------------------------------
    def get_zoom( self ):
        return self.zoom

    # ---------------------------------------------------------------------------------------

    def get_image( self, zoom, page ):
    
        if page < self.page_count:
            fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
            self.dlist = self.doc[ page ].get_displaylist()
            fitz.TOOLS.mupdf_display_errors(True)
    
            zoom_matrix = fitz.Matrix( zoom, zoom )
            return self.dlist.get_pixmap( alpha=False, matrix=zoom_matrix )
        else:
            return None
    
    # ---------------------------------------------------------------------------------------
    #   WRW 20 Apr 2022 - This is purely experimental. I want to see if there is any text, like a title,
    #       in the music books that appear to be scanned images.
    #   See: https://pymupdf.readthedocs.io/en/latest/tutorial.html#working-with-pages
    #   Could not find any. Oh, well.

    def get_text( self, page ):
    
        if page < self.page_count:
            fitz.TOOLS.mupdf_display_errors(False)      # Suppress error messages in books with alpha-numbered front matter.
            text = self.doc[ page ].get_text( 'text' )  # 'text' default
            fitz.TOOLS.mupdf_display_errors(True)
            return text
        else:
            return None
    
    # ---------------------------------------------------------------------------------------
    #   WRW 18 Apr 2022 - Added for image magnifier for Create Index.

    #   Get image from a square area of page mag_size big,
    #       at mag_zoom magnification,
    #       centered on mx, my in graph (not page) coordinates.

    #   Apply limits to coordinates here.
    #   This was another incredible pain to get working, fatigue mediated. Primary issue
    #   was that I neglected to understand that the clipping of a zoomed image returns
    #   an image size which is a factor of the zoom, not the size given by the clip rect.
    #   With that resolved all is OK.

    def get_magnified_pixmap( self, mx, my, mag_size, mag_zoom ):

        if not self.dlist:      
            return              # No image shown yet

        r = self.dlist.rect
        page_width =  (r.tr - r.tl).x       # Page coordinates
        page_height = (r.br - r.tr).y

        ms2 = mag_size/2
        cmx = mx / self.zoom            # translate graph to page coordinates.
        cmy = my / self.zoom

        cmx = max( ms2, cmx )           # Limit to bounds of page less half the size of magnification area.
        cmx = min( cmx, page_width - ms2 )

        cmy = max( ms2, cmy )
        cmy = min( cmy, page_height - ms2 )

        mag_clip = (cmx - ms2, cmy - ms2, cmx + ms2, cmy + ms2 )
        zoom_matrix = fitz.Matrix( mag_zoom, mag_zoom )     # returns transform matrix, array of six values.

        return self.dlist.get_pixmap( alpha=False, matrix=zoom_matrix, clip=mag_clip )

    # ---------------------------------------------------------------------------------------
    #   Returns the current page size in graph, not page, coordinates, i.e., adjusted for zoom.

    def get_current_page_size( self ):
        if not self.dlist:      
            return              # No image shown yet

        r = self.dlist.rect
        page_width =  (r.tr - r.tl).x * self.zoom                       
        page_height = (r.br - r.tr).y * self.zoom     

        return (page_width, page_height)

    # ---------------------------------------------------------------------------------------
    #   Get the contents of the image described by bounding box bb, in graph coordinates
    #   bb: [(tl_x, tl_y), (lr_x, lr_y)]
    #   clip: [tl_x, tl_y, lr_x, lr_y]

    def get_pixmap_from_bb( self, bb ):
        nbb = []
        nbb.append( bb[0][0] / self.zoom )
        nbb.append( bb[0][1] / self.zoom )
        nbb.append( bb[1][0] / self.zoom )
        nbb.append( bb[1][1] / self.zoom )

        #   Want 300 dpi. Images are 96 dpi in PDF. Zoom to 300 dpi.
        zoom = 300/96
        zoom_matrix = fitz.Matrix( zoom, zoom )   # Try larger zoom for better OCR? One doc said 300 dpi is standard.

        return self.dlist.get_pixmap( colorspace=fitz.csGRAY, alpha=False, matrix=zoom_matrix, clip=nbb )
      # return self.dlist.get_pixmap( colorspace=fitz.csGRAY, alpha=False, dpi=300, clip=nbb )

    # ---------------------------------------------------------------------------------------
    #   WRW 25 Mar 2022 - next_page() and prev_page() return True if hit bottom or top, False otherwise, i.e., new page.

    def first_page( self ):
        if self.doc:
            self.cur_page = 0
            self.refresh()
        #   self.window['hidden-page-change'].click()     # tell others there is a new page
            self.report_page_change()

    def next_page( self ):
        if self.doc:
            self.cur_page += 1
            if self.cur_page >= self.page_count:
                self.cur_page = self.page_count - 1
                limit = True
            else:
                limit = False
            #   self.window['hidden-page-change'].click()     # tell others there is a new page
                self.report_page_change()
                self.refresh()
            return limit

    def prev_page( self ):
        if self.doc:
            self.cur_page -= 1
            if self.cur_page < 0:
                self.cur_page = 0
                limit = True
            else:
                limit = False
            #   self.window['hidden-page-change'].click()     # tell others there is a new page
                self.report_page_change()
                self.refresh()
            return limit

    def last_page( self ):
        if self.doc:
            self.cur_page = self.page_count - 1
            self.refresh()
        #   self.window['hidden-page-change'].click()     # tell others there is a new page
            self.report_page_change()

    def goto_page( self, page ):        # WRW 18 Apr 2022 - added for Create Index
        if self.doc:
            self.cur_page = page - 1    # User page refs are 1-based
            if self.cur_page >= self.page_count:
                self.cur_page = self.page_count - 1

            elif self.cur_page < 0:
                self.cur_page = 0

            self.refresh()
            self.report_page_change()       # WRW 29 Apr 2022 - Added
            return None

    def get_cur_page(self):
        return self.cur_page + 1

    # def scroll_down( self ):
    #     if self.doc:

    # def scroll_up( self ):
    #     if self.doc:

    # ========================================================================================
    #   PDF-related events are processed here.       
    #   Return False if none recognized.

    def process_events( self, event, values ):
        # print( "/// pdf event:", event, "for:", self.for_txt )

        # ================================================================
        #   Keyboard Events, only when tab-display-pdf is selected.
        #   Had a nasty logic bug here, not helped by fatigue.
        #   I was entering block anytime tab-display-was selected, not just
        #       for keystrokes. Worked initially because it was the last 'if'.
        #       Failed when I moved it higher up.
        #   events in form "Next:117", "MouseWheel:Up", i.e., two parts separated by ':'
        #   WRW 26 Mar 2022 - Scrolling/key response was an incredible pain to get
        #       working well but it is now sensible, intuitive, and simpler code than earlier.
        #   WRW 25 Apr 2022 - I disabled keyboard events at the Window() level a few
        #       days ago - return_keyboard_events=False. Deal with them via bind() instead.
        #       Looks like capture <MouseWheel> does not work in graph(), will have to re-enable return_keyboard_events.
        #       Now only <MouseWheel> is processed here, all else with bound events.

        if ':' in event:                # WRW 26 Apr 2020 - Events filtered by tab earlier.

            t = event.split( ':' )      # We know a ':' is in event here, don't have to worry about 'ab' having len of 2.
            if len( t ) == 2:

                # ------------------------------------------------------------
                #   focus is same thing returned by window.Element('key')      

                focus = self.window.find_element_with_focus()
                # print( "*** focus", focus, "graph:", self.graph_element )

                if focus != self.graph_element:         # Remember, graph_element could be in Music Index or Create/Edit User Index
                    return False                        # Not our event.

                # ------------------------------------------------------------
                #   Scroll DOWN with mouse wheel / touchpad / Down key.
                #   Moves graph (viewing window) DOWN by moving pixmap up. Remember y == 0 in upper-left corner, + is down.

                if event in ( "MouseWheel:Down", "Down:116" ):

                    new_pixmap_y = self.current_pixmap_y if self.current_pixmap_y else 0
                    new_pixmap_y -= 20 if event == "MouseWheel:Down" else int( self.image.height * .1 )

                    (graph_width, graph_height) = self.graph_element.get_size()  # Size of graph element on screen
                    pixmap_bottom = new_pixmap_y + self.image.height    # Bottom of pixmap relative to graph top
                    pixmap_top = new_pixmap_y                           # Top of pixmap relative to graph top

                    if pixmap_bottom < graph_height:                    # Scroll/key past bottom of page?
                        limit = self.next_page()                        # Yes next_page() draws new page at 0,0
                        if not limit:
                            self.current_pixmap_y = 0                   # and update if not reach limit.

                    # Did not scroll/key past bottom of page, move top of image up to new_pixmap_y. Off top of graph.
                    else:                                                                                  
                        self.graph_element.relocate_figure( self.pdf_figure, 0, new_pixmap_y )
                        self.current_pixmap_y = new_pixmap_y

                    return True

                # ------------------------------------------------------------
                #   Scroll UP with mouse wheel / touchpad / Up key.
                #   Moves graph (viewing window) UP by moving pixmap down. Remember y == 0 in upper-left corner, + is down.
                #   Remember: relocate_figure() is a PySimpleGUI operation
                #       to move object in graph to absolute x, y position.
                #       Here y is 0 or negative. A negative y moves image up showing lower part of it.

                elif event in ("MouseWheel:Up", "Up:111" ):

                    new_pixmap_y = self.current_pixmap_y if self.current_pixmap_y else 0
                    new_pixmap_y += 20 if event == "MouseWheel:Up" else int( self.image.height * .1 )

                    (graph_width, graph_height) = self.graph_element.get_size()     # Size of graph element on screen
                    pixmap_bottom = new_pixmap_y + self.image.height
                    pixmap_top = new_pixmap_y

                    if pixmap_top > 0:                                                  # Top of pixmap below top of graph?
                        limit = self.prev_page()                                        # Yes, new page. prev_page() positions at top (0,0).
                        if not limit:
                            new_pixmap_y = - (self.image.height - graph_height )        # and position top of pixmap so bottom at bottom of graph
                            if new_pixmap_y > 0:                                        # unless would move top below top of graph
                                new_pixmap_y = 0                                        # then put top of pixmap at top of graph.

                            self.graph_element.relocate_figure( self.pdf_figure, 0, new_pixmap_y )
                            self.current_pixmap_y = new_pixmap_y

                    else:    # No, just draw pixmap at new position in graph
                        self.graph_element.relocate_figure( self.pdf_figure, 0, new_pixmap_y )
                        self.current_pixmap_y = new_pixmap_y 

                    return True

                # ------------------------------------------------------------

                elif event in ("Right:114", "Next:117", "Down:116" ):
                    self.next_page()
                    return True

                elif event in ("Left:113", "Prior:112", "Up:111"):
                    self.prev_page()
                    return True

                elif event in ("Home:110" ):
                    self.first_page()
                    return True

                elif event in ("End:115" ):
                    self.last_page()
                    return True

            return False         # Event not processed, propagate it

        # ================================================================
        #   WRW 25 Apr 2022
        #   Bound key events. Not using, went back to keyboard events.

        # elif event == 'display-graph-pdf-Left' or event == 'display-graph-pdf-Up':
        #     self.prev_page()
        #     return True

        # elif event == 'display-graph-pdf-Right' or event == 'display-graph-pdf-Down':
        #     self.next_page()
        #     return True

        # elif event == 'display-graph-pdf-Home':
        #     self.first_page()
        #     return True

        # elif event == 'display-graph-pdf-End':
        #     self.last_page()
        #     return True

        # ================================================================
        #   Zoom button events

        elif event == 'display-button-zoom-in':
            self.zoom *= 1.2
            self.fit = 'User'
            self.refresh()
            return True

        elif event == 'display-button-zoom-out':
            self.zoom *= 1/1.2
            self.fit = 'User'
            self.refresh()
            return True

        elif event == 'display-button-zoom-100':
            self.zoom = 1
            self.fit = 'Full'
            self.refresh()
            return True

        elif event == 'display-button-zoom-height':
            self.fit = 'Height'
            self.refresh()
            return True

        elif event == 'display-button-zoom-width':
            self.fit = 'Width'
            self.refresh()
            return True

        # -----------------------------------------------------
        #   Page change button events

        elif event == 'display-button-next':
            self.next_page()
            return True

        elif event == 'display-button-prev':
            self.prev_page()
            return True

        elif event == 'display-button-first':
            self.first_page()
            return True

        elif event == 'display-button-last':
            self.last_page()
            return True

        # -----------------------------------------------------
        #   Mouse drag to change page. Not a smooth drag but just to change page.
        #       This ONLY applies to Music Viewer tab and OK as is. Create Index
        #       uses mouse drag for drawing and zoom.
        #   /// RESUME OK - separate this from fb_pdf.py and into new code fb_music_viewer.py
        #       along with meta code. Someday.

        #   WRW 30 Dec 2021 - This was also an incredible pain to get working
        #       mostly because I had lost sleep and kept plodding along.
        #   WRW 26 Mar 2022 - Looks like PySimpleGUI blocks other events when
        #       mouse is down. Send 'hidden-page-change' when it comes up to update metadata.

        # --------------------------------------
        elif event == 'display-graph-pdf':                  
            mouse = values[ 'display-graph-pdf' ]           
            self.graph_element.set_focus()                  

            # ------------------------------
            if self.mouse_state == 'up':
                self.mouse_state = 'down'
                self.mouse_start_pos = mouse
                return True

            # ------------------------------
            #   WRW 25 Mar 2022 - Don't move page in window on mouse movement, just change page. Works
            #   far more intuitively and what mupdf does. Okular does not as mouse used for selection.

            elif self.mouse_state == 'down':                                                                       
                delta_y = self.mouse_start_pos[1] - mouse[1]
                abs_delta_y = -delta_y if delta_y < 0 else delta_y

                if abs_delta_y > 20:        # Hysterisis, definitely need a little.
                   if delta_y > 0:
                       self.next_page()
                   else:
                       self.prev_page()
                return True

            return False

        # --------------------------------------
        elif event == 'display-graph-pdf+UP':
            self.mouse_state = 'up'
          # self.window['hidden-page-change'].click()     # May have new page but event blocked when mouse down.
            self.report_page_change()
            return True

        # ================================================================
        #   Moved from bluebird.py

        # elif event == 'Config-Event':

        elif event == 'display-graph-pdf-Config-Event':
            if values[ "main-tabgroup" ] == 'tab-display-pdf':
                self.refresh()
            return True

        # ----------------------------------------------
        #   Event not processed, tell calling routine to go on.

        else:
            return False

        # ----------------------------------------------
        #   Event processed if don't hit else above.

        print( "ERROR-DEV: How'd we get here?", file=sys.stderr )
        return False

    # ========================================================================================
