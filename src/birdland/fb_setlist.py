#!/usr/bin/python
# ---------------------------------------------------------------------------
#   fb_setlist.py

#   WRW 23 Jan 2022 - Setlist routines, pulled out of fb_utils.
#   Need to think about inheritance instead of passing pdf, fb, etc. into here
#   /// RESUME WRW 25 Jan 2022 - Getting more than one 'setlist-table' event after
#       select setlist from the Combo menu and setlist_show(). All else looks OK.
#       WRW 26 Jan 2022 - With approach from Jason it looks like problem is resolved.
#       See fb.safe_update().
#   /// RESUME Think I found where extra event came from. Go back to earlier Suppress logic to test.
#           At end of add.
#   /// RESUME Some crashes on some paths through the code. Better have a close look at it,
#       e.g., adding, deleting, moving, selecting. Think about corner cases.             

#   Save but not useful so far:
#       print( "/// qsize after update", self.window.thread_queue.qsize() )           

# ---------------------------------------------------------------------------

from pathlib import Path
import json
import sys

Test_Select_Suppress = True  # - to use select suppression, one still leaking through
Test_Select_Suppress = False # - to use Jason's approach to suppress prior to updating

class Setlist():

    # ---------------------------------
    def __init__( self ):
        self.setlist = None
        self.current_setlist_name = None
        self.suppress_setlist_table_event = False

    # ---------------------------------
    def set_class_config( self ):
        self.SetListFile = self.conf.val( 'setlistfile' )                        
        self.MusicFileRoot = self.conf.val( 'music_file_root' )                        
        self.UseExternalMusicViewer =   self.conf.val( 'use_external_music_viewer' )

    # ---------------------------------
    def set_dc( self, dc ):
        self.dc = dc

    # ---------------------------------

    def set_icon( self, t ):
        global BL_Icon
        BL_Icon = t

    # ---------------------------------

    def set_classes( self, conf, sg, fb, pdf, meta, toc ):
        self.conf = conf
        self.sg = sg
        self.fb = fb
        self.pdf = pdf
        self.meta = meta
        self.toc = toc

    # ---------------------------------------------------

    def set_elements( self, window, ele_setlist_table, ele_tab_display_pdf, ele_setlist_move_up,
                            ele_setlist_move_down, ele_setlist_delete,
                            ele_setlist_save_menu, ele_setlist_controls_menu,
                            ele_tab_setlist_table,
                     ):

        self.window = window
        self.ele_setlist_table = ele_setlist_table
        self.ele_tab_display_pdf = ele_tab_display_pdf
        self.ele_setlist_move_up = ele_setlist_move_up
        self.ele_setlist_move_down = ele_setlist_move_down 
        self.ele_setlist_delete = ele_setlist_delete
        self.ele_setlist_save_menu = ele_setlist_save_menu
        self.ele_setlist_controls_menu = ele_setlist_controls_menu
        self.ele_tab_setlist_table = ele_tab_setlist_table 

    # ---------------------------------------------------
    #   Must maintain setlist data structure separate from setlist table.

    def setlist_save_to_table( self, id, title, canonical, src, local, sheet, page, file ):
        if not self.setlist:
            self.setlist = {}
        if id not in self.setlist:
            self.setlist[ id ] = []

            #   WRW 25 Jan 2022 - Update setlist Combo box menus with new id.

            sl_names = self.setlist_get_names()
            self.ele_setlist_save_menu.update( values = sl_names, value=self.current_setlist_name )
            self.ele_setlist_controls_menu.update( values = sl_names, value=self.current_setlist_name )

        self.setlist[ id ].append( { 'title' : title, 
                                     'canonical' : canonical,
                                     'src' : src,
                                     'local' : local,
                                     'sheet' : sheet,
                                     'page' : page,
                                     'file' : file } )
    
    # ---------------------------------------------------
    def setlist_get( self, id ):
        if not self.setlist or id not in self.setlist:
            return None
        else:
            return self.setlist[ id ]

    # ---------------------------------------------------
    def setlist_get_current( self ):
        return self.setlist_get( self.current_setlist_name )

    # ---------------------------------------------------
    def setlist_load( self ):
        setlist_path = Path( self.SetListFile )
        if setlist_path.is_file():
            try:
                t = json.loads( setlist_path.read_text() )
                self.setlist = t[ 'setlist' ]
                self.current_setlist_name = t[ 'current' ]
                return t[ 'current' ]
            except:
                self.setlist = []
                self.current_setlist_name = 'Default'
                return 'Default'
        else:
            self.setlist = []
            self.current_setlist_name = 'Default'
            return 'Default'

    # ---------------------------------------------------
    def setlist_save( self ):
        setlist_path = Path( self.SetListFile )
        t = { 'current' : self.current_setlist_name, 'setlist' : self.setlist }
        setlist_path.write_text( json.dumps( t, indent=2 ) )

        self.conf.do_popup( f"\nSetlist '{self.current_setlist_name}' saved to:\n{setlist_path}\n" )

        # self.sg.popup_auto_close( f"\n  Setlist {self.current_setlist_name} saved to:\n  {setlist_path}  \n",
        #     auto_close_duration = .7,
        #     modal = True,
        #     keep_on_top = True,
        # )

    # ---------------------------------------------------
    #   Show current setlist in setlist tab.
    #   Start with none selected. Otherwise selected row was displayed.
    #   Called from bluebird.py initialize_gui(), which is after wait for graph in timeout loop.
    #   /// RESUME - this part of larger problem here when set select_rows
    #   update.table( select_rows = [0] ) causes two 'setlist-table' events.
    #   Looks like I had not commented out the update() without the select_rows so that
    #   I was getting the event for the select_rows but the selection was empty because
    #   of the second update(). Don't know why two events.

    def setlist_show( self, id ):
        self.current_setlist_name = id
        sl = self.setlist_get( id )

        if sl:
            values = [ [ x[ 'title' ], x[ 'canonical' ], x[ 'file' ], x[ 'page' ] ] for x in sl ]
            if Test_Select_Suppress:
                print( "/// setlist_show() updating table with suppress set" )
                print( "/// setting suppress" )
                self.fb.log( "/// setting suppress", "setlist_show()" )

                self.suppress_setlist_table_event = True
                self.ele_setlist_table.update( values=values, select_rows = [0] )        # /// RESUME - prob if set. Now suppressed.

            else:
                self.fb.safe_update( self.ele_setlist_table, values, [0] )

          # self.ele_setlist_table.update( values=values )

    # ---------------------------------------------------
    def setlist_get_names( self ):
        return [ x for x in self.setlist ]

    # ---------------------------------------------------
    def setlist_get_item( self, index ):
        return self.setlist[ self.current_setlist_name ][ index ]

    # ---------------------------------------------------
    def setlist_get_current_len( self ):
        return len( self.setlist[ self.current_setlist_name] )

    # ----------------------------------------------------------------------------
    #   /// RESUME - some funnies here when item in setlist table is selected
    #       just like I saw earlier in other tables that caused me to force deselect
    #       after showing. That problem disappeared.
    #   Example: select setlist in manage setlist Combo and first title is shown in PDF Tab.
    #   /// RESUME Getting two 'setlist-table' events at startup, no idea why, but only if
    #       but only table.update select_rows in setlist_show.

    def process_events( self, event, values ):

        # print( f"sl.process_events() Event: {event}\n  Suppress: {self.suppress_setlist_table_event}\n  Values: {values}\n\n" );

        # print( f"SETLIST process_events() Event: {event}, Suppress: {self.suppress_setlist_table_event}" );

        # ------------------------------------------------------------------
        #   User selected setlist from Combo dropdown menu

        if event == 'setlist-controls-menu':
            setlist_id = values[ 'setlist-controls-menu' ]
            self.setlist_show( setlist_id )
            self.ele_setlist_save_menu.update( value=setlist_id)        # Update save menu selection, too.
            return True

        # ------------------------------------------------------------------
        #   *** Click in setlist table. Play clicked file if not in edit mode.
        #       Expect to find 'setlist-table' in values.
        #       WRW 27 Jan 2022 - RESUME track down where extra one comes from after select id from menu
        #       WRW 28 Jan 2022 - Now use file, not canonical, to identify file.
        #       WRW 2 Feb 2022 - Include all metadata in setlist

        elif event == 'setlist-table':

            #   /// RESUME 25 Jan 2022 - This terrible hack is needed until PySimpleGui provides a way to suppress
            #       the event on Table.update( select_rows = [...] )
            #   Actually, appears to work pretty well... at least after a brief test.

            if self.suppress_setlist_table_event:
                self.suppress_setlist_table_event = False
                print( "--- Suppressing" )
                return True

            if not values[ 'setlist-edit' ]:
                if 'setlist-table' in values and len( values[ "setlist-table" ] ):
                    index = values[ "setlist-table" ][0]
                    item = self.setlist_get_item( index )       # item is one row of the internal setlist data structure.

                    title       = item[ 'title' ]
                    canonical   = item[ 'canonical' ]
                    src         = item[ 'src' ]
                    local       = item[ 'local' ]
                    page        = item[ 'page' ]
                    sheet       = item[ 'sheet' ]
                    rel_path    = item[ 'file' ]

                    # rel_path = self.fb.get_file_by_canonical( canonical )
                    if rel_path:
                        full_path = Path( self.MusicFileRoot, rel_path ).as_posix()

                        #   /// RESUME - cleanup metadata for setlist item with partial data
                        #   /// WRW 2 Feb 2022 - Try using meta.show()
                        self.pdf.show_music_file( file=full_path, page=page )       # Click in setlist
                        if False:
                            self.meta.show_from_setlist( rel_path,
                                            page,
                                            self.pdf.get_info()[ 'page_count' ],
                                            title,
                                            src,
                                            local,
                                            canonical )
                        else:
                            self.meta.show( 
                                       id='SetList',
                                       file=rel_path,
                                       title=title,
                                       canonical=canonical,
                                       src=src,
                                       local=local,
                                       sheet=sheet,
                                       page=page,
                                       page_count = self.pdf.get_info()[ 'page_count' ],
                                       )

                        self.toc.show( canonical=canonical )
                        # self.toc.show( file = rel_path )

                        if not self.UseExternalMusicViewer:
                            self.ele_tab_display_pdf.select()
                            self.ele_tab_display_pdf.set_focus()

                    else:
                        # self.sg.popup( f"\nNo music file for:\n\n   '{title}'\n\n    From: {canonical}\n",
                        self.sg.popup( f"\nMusic file '{file}'\n\n   not found in music library.\n",
                            title='Warning',
                            icon='BL_Icon',
                            keep_on_top = True,
                        )
                else:
                    # print( f"BUG: Unexpected 'values[ 'setlist-table' ]' for event: 'setlist-table'", file=sys.stderr )
                    # for x in sorted( values ):
                    #     print( f"{x:>30}: {values[x]}", file=sys.stderr )

                    t = [ f"{x:>30}: {values[x]}" for x in sorted( values ) ]
                    t.insert( 0, f"BUG: Unexpected 'values[ 'setlist-table' ]': '{values[ 'setlist-table' ]}' for event: 'setlist-table'\n" )
                    self.sg.popup( '\n'.join(t),
                                   title='Bug',
                                   icon='BL_Icon',
                                   background_color='#000060',
                                   text_color = '#ffffff',
                                   font=("Courier", 11),
                                   keep_on_top = True,
                                )
            return True

        # ------------------------------------------------------------------
        #   WRW 25 Jan 2022 - Make setlist to which the item was added the current setlist.
        #   WRW 28 Jan 2022 - Make title, canonical and page optional, file is not optional.
        #   WRW 2 Feb 2022 - Include src & local in setlist so can navigate after a setlist selection.
        #   Data obtained from metadata info.

        elif event == 'display-button-add-to-setlist':
            setlist_id = values[ 'setlist-save-menu' ]

            metadata = self.meta.get_info()
            # print( f"/// At add, titles: {metadata[ 'titles' ]}, canonical: {metadata[ 'canonical']}, page: {metadata['page']}" )

            if 'file' in metadata:
                file = metadata[ 'file' ]

                # ----------------------------------------------
                #   Avoid pathological case.

                if file == self.fb.get_docfile():
                    self.sg.popup( "\nStop fooling around.\nCan't add the help file to a setlist.\n",
                                   title='Warning',
                                   icon='BL_Icon',
                                   keep_on_top = True,
                                )
                    return True

                # ----------------------------------------------
                #   Add to self.setlist internal data structure.

                page = metadata[ 'page' ] if 'page' in metadata else None
                canonical = metadata[ 'canonical' ] if 'canonical' in metadata else None
                titles = metadata[ 'titles' ] if 'titles' in metadata else None
                src = metadata[ 'src' ] if 'src' in metadata else None
                local = metadata[ 'local' ] if 'local' in metadata else None
                sheet = metadata[ 'sheet' ] if 'sheet' in metadata else None

                #   May have multiple titles on one page, add them all.
                if titles:
                    for title in metadata[ 'titles' ]:
                        self.setlist_save_to_table( setlist_id, title, canonical, src, local, sheet, page, file )
                else:
                    self.setlist_save_to_table( setlist_id, None, canonical, src, local, sheet, page, file )

                # -------------------------------------------------------
                #   Update setlist table and select last item added.
                #   Get data from internal data structure for the setlist indicated by 'setlist_id'.

                sl_list = self.setlist_get( setlist_id )
                if sl_list:
                    values = [ [ x[ 'title' ], x[ 'canonical' ], x[ 'file' ], x[ 'page' ] ] for x in sl_list ]

                    if Test_Select_Suppress:
                        print( "/// setting suppress" )
                        self.fb.log( "/// setting suppress", "add to setlist" )
                        self.suppress_setlist_table_event = True
                        self.ele_setlist_table.update( values=values, select_rows = [len(sl_list) -1] )   # select last added item after add.
                    else:
                        self.fb.safe_update( self.ele_setlist_table, values, [len(sl_list) -1] )

                self.setlist_save()

                # -------------------------------------------------------
                #   After addition make the added-to list current and selected in the Combo menus.
                #   Show the setlist table.

                self.ele_setlist_save_menu.update( value=setlist_id )
                self.ele_setlist_controls_menu.update( value=setlist_id)
                self.ele_tab_setlist_table.select()

                # self.setlist_show( setlist_id )   # This may have been causing the extra event

            return True

        # ----------------------------------------------------------------

        elif event == 'setlist-edit':
            if values[ 'setlist-edit' ]:
                self.ele_setlist_move_up.update( disabled = False )
                self.ele_setlist_move_down.update( disabled = False )
                self.ele_setlist_delete.update( disabled = False )

                if not 'setlist-table' in values or len( values[ 'setlist-table'] ) == 0:

                    if Test_Select_Suppress:
                        print( "/// setting suppress" )
                        self.suppress_setlist_table_event = True
                        self.ele_setlist_table.update( select_rows = [0] )      # start with row 0 selected if none selected.

                    else:
                        self.fb.safe_update( self.ele_setlist_table, None, [0] )


            else:
                self.ele_setlist_move_up.update( disabled = True)
                self.ele_setlist_move_down.update( disabled = True )
                self.ele_setlist_delete.update( disabled = True )

            return True

        # ----------------------------------------------------------------

        elif event == 'setlist-move-up':
            items = self.setlist_get_current()
            if 'setlist-table' in values and len( values[ "setlist-table" ]):
                index = values[ "setlist-table" ][0]

            else:
                index = len(items) - 1

            nindex = index - 1

            if nindex >= 0 and items:
                item = items.pop( index )
                items.insert( nindex, item )
                values = [ [ x[ 'title' ], x[ 'canonical' ], x[ 'page' ] ] for x in items ]

                if Test_Select_Suppress:
                    print( "/// setting suppress" )
                    self.suppress_setlist_table_event = True
                    self.ele_setlist_table.update( values=values, select_rows = [nindex] )
                else:
                    self.fb.safe_update( self.ele_setlist_table, values, [nindex] )

            return True

        # ----------------------------------------------------------------
        elif event == 'setlist-move-down':
            items = self.setlist_get_current()
            if 'setlist-table' in values and len( values[ "setlist-table" ]):
                index = values[ "setlist-table" ][0]
            else:
                index = 0

            nindex = index + 1
            if nindex < len( items ):
                item = items.pop( index )
                items.insert( nindex, item )
                values = [ [ x[ 'title' ], x[ 'canonical' ], x[ 'page' ] ] for x in items ]

                if Test_Select_Suppress:
                    print( "/// setting suppress" )
                    self.suppress_setlist_table_event = True
                    self.ele_setlist_table.update( values=values, select_rows = [nindex] )
                else:
                    self.fb.safe_update( self.ele_setlist_table, values, [nindex] )

            return True

        # ----------------------------------------------------------------
        elif event == 'setlist-delete':
            items = self.setlist_get_current()

            if 'setlist-table' in values and len( values[ "setlist-table" ]):
                index = values[ "setlist-table" ][0]
            else:
                index = 0

            if items:
                item = items.pop( index )

                index -= 1
                if index < 0:
                    index = 0
                values = [ [ x[ 'title' ], x[ 'canonical' ], x[ 'page' ] ] for x in items ]
                if values:
                    if Test_Select_Suppress:
                        print( "/// setting suppress" )
                        self.suppress_setlist_table_event = True
                        self.ele_setlist_table.update( values=values, select_rows = [index] )
                    else:
                        self.fb.safe_update( self.ele_setlist_table, values, [index] )
                else:
                    if Test_Select_Suppress:
                        print( "/// setting suppress" )
                        self.suppress_setlist_table_event = True
                        self.ele_setlist_table.update( values=values, select_rows = None )
                    else:
                        self.fb.safe_update( self.ele_setlist_table, values, None )

            return True

        # ----------------------------------------------------------------
        elif event == 'setlist-save':
            self.setlist_save()

        # ----------------------------------------------------------------------------
        else:
            # print( "--- Ignored" )
            return False

    # ----------------------------------------------------------------------------
