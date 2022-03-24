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
#   Internal page numbers here are 0-based.

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
        self.fit = 'Height'
        self.current_file = None
        self.page_count = None
        self.cur_page = 0

        self.mouse_curr = None
        self.mouse_start_pos =  None
        self.mouse_release_pos =  (0,0)
        self.mouse_state = 'up'

        self.music_popen = None
        self.UseExternalMusicViewer = None

        self.external_viewer = False

    # --------------------------------------------------------------

    def set_classes( self, conf ):
        self.conf = conf

    # --------------------------------------------------------------

    def set_class_config( self ):
        self.UseExternalMusicViewer =   self.conf.val( 'use_external_music_viewer' )
        self.ExternalMusicViewer    =   self.conf.val( 'external_music_viewer' )
        self.MusicFileRoot          =   self.conf.val( 'music_file_root' )

    # --------------------------------------------------------------
    def set_window( self, window ):      # PySimpleGui window
        self.window = window

    # --------------------------------------------------------------
    def set_graph_element( self, graph_element ):      # PySimpleGui Graph element
        self.graph_element = graph_element

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

                self.doc = fitz.open( file )
                self.page_count = self.doc.page_count
                self.current_file = file

        # ----------------------------------------
        #   Delete prior figure in graph, if any.

        if self.pdf_figure:
             self.graph_element.delete_figure( self.pdf_figure )

        # ----------------------------------------
        #   A little initialization of mouse-movement parameters

        self.mouse_release_pos = (0,0)
        self.mouse_start_pos = None,
        self.mouse_state = 'up'
        self.mouse_curr = None

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
    #   /// RESUME - this could use a little more work to preserve location on page during zoom and resize.
    #       Rethink mouse_curr as more than mouse.

    def refresh( self ):
        if self.external_viewer:
            return

        self.mouse_release_pos = (0, 0)     #   WRW 22 Jan 2022 - A little more initialization when go to new page
        self.mouse_start_pos = None
        self.mouse_state = 'up'

        if self.pdf_figure:     # Delete current image
             self.graph_element.delete_figure( self.pdf_figure )

        zoom = self.get_zoom_from_fit()

        self.image = self.get_image( zoom, self.cur_page )
        if self.image:
            self.pdf_figure = self.graph_element.draw_image( data = self.image.tobytes(), location = (0, 0) )

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

    def get_zoom_from_fit( self ):
        if self.doc:
            graph_width, graph_height = self.graph_element.get_size()
    
            if self.fit == 'Full':
                self.zoom = 1
    
            elif self.fit == 'Height':
                if self.cur_page < len(self.doc):
                    fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
                    r = self.doc[self.cur_page].get_displaylist().rect
                    fitz.TOOLS.mupdf_display_errors(True)
                    page_height = (r.br - r.tr).y
                    self.zoom = graph_height / page_height
    
            elif self.fit == 'Width':
                if self.cur_page < len(self.doc):
                    fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
                    r = self.doc[self.cur_page].get_displaylist().rect
                    fitz.TOOLS.mupdf_display_errors(True)
                    page_width = (r.tr - r.tl).x
                    self.zoom = graph_width / page_width
    
            # elif self.fit == 'User':        # After user adjusted zoom setting with +/-.
            #     return self.zoom

        else:
            self.zoom = 1

        return self.zoom
    
    # ---------------------------------------------------------------------------------------

    def get_image( self, zoom, page ):
    
        if page < self.page_count:
            fitz.TOOLS.mupdf_display_errors(False)  # Suppress error messages in books with alpha-numbered front matter.
            dlist = self.doc[ page ].get_displaylist()
            fitz.TOOLS.mupdf_display_errors(True)
    
            zoom_matrix = fitz.Matrix( zoom, zoom )
            return dlist.get_pixmap( alpha=False, matrix=zoom_matrix )
        else:
            return None
    
    # ---------------------------------------------------------------------------------------

    def first_page( self ):
        if self.doc:
            self.cur_page = 0
            self.refresh()
            self.window['hidden-page-change'].click()     # tell others there is a new page

    def next_page( self ):
        if self.doc:
            self.cur_page += 1
            if self.cur_page >= self.page_count:
                self.cur_page = self.page_count - 1
            self.refresh()
            self.window['hidden-page-change'].click()     # tell others there is a new page

    def prev_page( self ):
        if self.doc:
            self.cur_page -= 1
            if self.cur_page < 0:
                self.cur_page = 0
            self.refresh()
            self.window['hidden-page-change'].click()     # tell others there is a new page

    def last_page( self ):
        if self.doc:
            self.cur_page = self.page_count - 1
            self.refresh()
            self.window['hidden-page-change'].click()     # tell others there is a new page

    # def scroll_down( self ):
    #     if self.doc:

    # def scroll_up( self ):
    #     if self.doc:

    # ========================================================================================
    #   PDF-related events are processed here.       
    #   Return False if none recognized.

    def process_events( self, event, values ):

        # ================================================================
        #   Keyboard Events, only when tab-display-pdf is selected.
        #   Had a nasty logic bug here, not helped by fatigue.
        #   I was entering block anytime tab-display-was selected, not just
        #       for keystrokes. Worked initially because it was the last 'if'.
        #       Failed when I moved it higher up.
        #   events in form "Next:117", "MouseWheel:Up", i.e., two parts separated by ':'

        if ':' in event and values[ 'main-tabgroup' ] == 'tab-display-pdf':

            t = event.split( ':' )      # We know a ':' is in event here, don't have to worry about 'ab' having len of 2.
            if len( t ) == 2:

                # ------------------------------
                #   focus is same thing returned by window.Element('key')      

                focus = self.window.find_element_with_focus()

                # ----------------------------------------------
                #   Scroll DOWN with mouse wheel / touchpad

                if event in ( "MouseWheel:Down", "Down:116" ) and focus == self.graph_element:

                    nx = 0              # Must define this
                    ny = self.mouse_curr[1] if self.mouse_curr else 0
                    ny -= 20 if event == "MouseWheel:Down" else int( self.image.height / 3 )
                    # ny -= 20 if event == "MouseWheel:Down" else 60

                    # pixmap_height = self.pdf_pixmap.height
                    pixmap_height = self.image.height
                    (width, height) = self.graph_element.get_size()     # /// RESUME - get this just once?
                    bottom = ny + pixmap_height
                    top = ny

                    if bottom < height:
                        self.next_page()
                        self.mouse_curr = (0, 0)

                    else:
                        self.graph_element.relocate_figure( self.pdf_figure, nx, ny )
                        self.mouse_curr = (nx, ny)

                    #   Save in case user uses mouse after scrolling
                    self.mouse_release_pos = self.mouse_curr

                # ----------------------------------------------
                #   Scroll UP with mouse wheel / touchpad
                #   RESUME - here and above - click up to top/bottom of page then go to next

                elif event in ("MouseWheel:Up", "Up:111" ) and focus == self.window.Element( 'display-graph-pdf'):

                    nx = 0              # Must define this
                    ny = self.mouse_curr[1] if self.mouse_curr else 0
                    # ny += 20 if event == "MouseWheel:Down" else int( self.image.height / 3 )
                    ny += 20 if event == "MouseWheel:Down" else 60

                    # pixmap_height = self.pdf_pixmap.height
                    pixmap_height = self.image.height
                    (width, height) = self.graph_element.get_size()      # /// RESUME - just once?
                    bottom = ny + pixmap_height
                    top = ny

                    if top > 0:
                        self.prev_page()
                        ny = height - pixmap_height
                        self.graph_element.relocate_figure( self.pdf_figure, nx, ny )
                        self.mouse_curr = (0, ny)

                    else:
                        self.graph_element.relocate_figure( self.pdf_figure, nx, ny )
                        self.mouse_curr = (nx, ny)

                    #   Save in case user uses mouse after scrolling
                    self.mouse_release_pos = self.mouse_curr

                # ------------------------------

                elif event == "Next:117" and focus == self.window.Element( 'display-graph-pdf'):
                    self.next_page()

                elif event == "Prior:112" and focus == self.window.Element( 'display-graph-pdf'):
                    self.prev_page()

                # elif event == "Down:116" and focus == self.window.Element( 'display-graph-pdf'):
                #     self.scroll_down()

                # elif event = "Up:111" and focus == self.window.Element( 'display-graph-pdf'):
                #     self.scroll_up()

                elif event in ("Home:110" ):
                    self.first_page()

                elif event in ("End:115" ):
                    self.last_page()
            return True

        # ================================================================
        #   Zoom events
        #   Add zoom limits? Maybe not.

        elif event == 'display-button-zoom-in':
            self.zoom *= 1.2
            self.fit = 'User'
            self.refresh()
            return True

        elif event == 'display-button-zoom-out':
            self.zoom *= .8
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
        #   Page change events

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
        #   Mouse / Kbd events
        # -----------------------------------------------------
        #   WRW 30 Dec 2021 - This was an incredible pain to get working 
        #       mostly because I had lost sleep and kept plodding along.

        elif event == 'display-graph-pdf+UP':
            if self.mouse_curr:
                self.mouse_release_pos = self.mouse_curr
                self.mouse_state = 'up'
            return True

        # --------------------------------------
        elif event == 'display-graph-pdf':
            mouse = values[ 'display-graph-pdf' ]
            self.graph_element.set_focus()

            # ------------------------------
            if self.mouse_state == 'up':
                self.mouse_state = 'down'

                if self.mouse_release_pos:

                  # nx = Graph['mouse_release_pos'][0]      # this allows image to float in x
                    nx = 0  # This keeps the image locked to the left side
                    ny = self.mouse_release_pos[1]

                else:
                    nx = ny = 0

                self.mouse_start_pos = mouse

            # ------------------------------
            elif self.mouse_state == 'down':       # Mouse moving, calculat position rel to position when mouse up.

                if self.mouse_release_pos:         # In case user clicks in window before anything shown
                  # nx = PDF_Display[ 'mouse_release_pos' ][0] + ( mouse[0] - PDF_Display['mouse_start_pos'][0] )
                    nx = 0
                    ny = self.mouse_release_pos[1] + ( mouse[1] - self.mouse_start_pos[1] )

                # ------------------------------
                #  Change page on vertical movement past top and bottom
                #   Need a little hysterisis on mouse movement before even considering next & prev

                delta_y = self.mouse_start_pos[1] - mouse[1]
                delta_y = -delta_y if delta_y < 0 else delta_y

                if delta_y > 0:

                   (width, height) = self.graph_element.get_size()
                   bottom = ny + self.image.height
                   top = ny

                   # print( f"pixmap top: {top}, pixmap bottom: {bottom}, window height: {height}" )

                   if bottom < height:
                       self.next_page()

                   if top > 0:
                       self.prev_page()

            # ------------------------------
            #   /// RESUME - should some of this be in above?

            self.graph_element.relocate_figure( self.pdf_figure, nx, ny )
            self.mouse_curr = (nx, ny)
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

        print( "/// How'd we get here" )
        return False

    # ========================================================================================
