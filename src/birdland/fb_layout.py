#!/usr/bin/python

# --------------------------------------------------------------------------------
#   fb_layout.py 

#   wrw 23 Jan 2022  - Moved layout from bluebird.py.

# --------------------------------------------------------------------------------
#   Define Layout
#   Setting column width with values created one blank row, which can be clicked producing
#       prog errors.

#   Must have sg.TreeData() in initial call to sg.Tree(), can update data later.

# ================================================================================

import os

Bluebird_Program_Title = "Birdland Musician's Assistant"
Bluebird_Program_SubTitle = "A Multimedia Music Viewer"

MyTableColors = True
MyTableColors = False

if MyTableColors:
    Selected_Color    = '#ff0000'       # Table row colors
    Background_Color  = '#f0f0f0'
    Alternating_Color = '#d0d0ff'
    Text_Color        = '#000000'

else:
    Selected_Color    = None
    Background_Color  = None
    Alternating_Color = None
    Text_Color        = None

Table_Font        = ("Helvetica", 9)
Table_Font_Small  = ("Helvetica", 8)

Table_Row_Height  = 20                  # pixels
Table_Row_Height_Small  = 16                  # pixels
Table_Row_Count   = 20

Short_Table_Row_Count   = Table_Row_Count - 5       # For tables in sub-tabs

Tab_Font          = ("Helvetica", 9)

Tree_Font         = ("Helvetica", 9)

search_title_font = ("Helvetica", 10 )
pdf_display_control_text_box_size = 35
pdf_metadata_text_box_size = 30
GraphBackground   = None

Current_Table_Font        = ("Helvetica", 8)
Current_Table_Row_Height  = 18                  # pixels

# ================================================================================
#   Moved into a function so that it is not executed when loaded but when called
#       to pick up value of Table_Row_Count.

def get_layout( sg, fb, conf ):

    BL_Icon = fb.get_bl_icon()

    if not MyTableColors:

        #   These are tuned specifically for 'Dark'. Otherwise let PSG choose colors.
        if sg.theme() == 'Dark':
            Background_Color  = '#4d4d4d'
            Alternating_Color = '#3d3d3d'
        else:
            Background_Color  = None
            Alternating_Color = None

    # --------------------------------------------------------------------------------
    #   Hidden button defs. These are used to trigger events in main event loop.
    
    #     Generate event as if from PySimpleGui. Include hidden button and call click()
    #     Trigger with: self.window['hidden-page-change'].click()     # tell others there is a new page
    #     sg.Button( key='hidden-new-pdf', visible=False ),
    
    hidden_buttons = [
        sg.Button( key='pdf-hidden-page-change', visible=False ),
        sg.Button( key='ci-hidden-page-change', visible=False ),
    ]
    
    # --------------------------------------------------------------------------------
    #   Left tab group definitions
    
    selected_book_info = \
        sg.Text( text='\n\n',
                 key='browse-book-info',
                 font=("Helvetica", 9),
                 justification='left',
                 pad=((8,8),(0, 0)),
        )

    selected_book_info_frame = sg.Frame( 'Selected Music File Information',
              [[selected_book_info]],
              font=("Helvetica", 8),
              element_justification = 'left',
              pad = ((8,8), (10,0)),
              vertical_alignment='top',
              expand_x = True,
            )

    browse_src_title = \
        sg.Text( text='Select src for offsets for selected music file:',
                 key='browse-src-title',
                 font=("Helvetica", 9),
                 justification='left',
                 pad=((8,8),(10, 0)),
        )

    # srcs = fb.get_srcs()
    # priority_src = fb.get_priority_src()
    # print( priority_src )

    browse_src_combo = \
        sg.Combo(
              [],
              # srcs,
              # default_value = priority_src,
              key = 'browse-src-combo',
              font=("Helvetica", 10),
              pad=((8,8),(5,0)),
              auto_size_text = True,
              size = 10,
              enable_events = True,
              expand_x = True
        )

    browse_music_files = [
        [ selected_book_info_frame ],
        [ browse_src_title ],
        [ browse_src_combo ],
        [ sg.Tree( data = sg.TreeData(),
            key='browse-music-files',
            font=Tree_Font,
            pad=[(0, 0), (10, 0)],
            headings=[],
            auto_size_columns=True,
            justification = "left",
            col0_width = 30,
            enable_events=True,
            show_expanded=False,
            row_height = 22,
            expand_x = True,
            expand_y = True,
        )]
    ]
    
    browse_audio_files = [[
        sg.Tree( data = sg.TreeData(),
             key='browse-audio-files',
             font=Tree_Font,
             pad=[(0, 0), (10, 0)],
             headings=[],
             auto_size_columns=True,
             justification = "left",
             col0_width = 30,
             show_expanded=False,
             enable_events=True,
             row_height = 22,
             expand_x = True,
             expand_y = True,
        ),
    ]]
    
    table_of_contents_table = [[                  # Table of contents
        sg.Table(
            key='table-of-contents-table',
            font=Table_Font,
            row_height = Table_Row_Height,
            col_widths = [ 25, 5 ],
            # default_col_width = 10,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # visible_column_map = [ True, True ],
            pad=[(0, 0), (10, 0)],
            values=[[" ", " " ]],
            select_mode = None,
            headings = [ "Title", "Sheet" ],
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]
    
    current_audio_table = [[                  # Audio matching current PDF
        sg.Table(
            key='current-audio-table',
            headings = [ "Title", "Artist", "File" ],
            visible_column_map = [ True, True, False ],
            font=Current_Table_Font,
            row_height = Current_Table_Row_Height,
            # col_widths = [ 25, 5 ],
            # default_col_width = 10,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            auto_size_columns = True,  # Must be false for col_width to work.
            justification = 'left',
            pad=[(0, 0), (10, 0)],
            values=[[" ", " ", " "]],
            select_mode = None,
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]

    current_midi_table = [[                  # Midi matching current PDF
        sg.Table(
            key='current-midi-table',
            headings = [ "Path", "File" ],
            visible_column_map = [ False, True ],
            font=Current_Table_Font,
            row_height = Current_Table_Row_Height,
            # col_widths = [ 25, 5 ],
            # default_col_width = 10,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            auto_size_columns = True,  # Must be false for col_width to work.
            justification = 'left',
            pad=[(0, 0), (10, 0)],
            values=[[ "", ""]],
            select_mode = None,
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]
    
    # --------------------------------------------------------------------------------
    #   Note that the col_widths give here are intentionally small to keep the
    #   default width of the table reasonable. They will expand when the window
    #   is enlarged.
    
    # values=[[ " "*30 , " "*15, " "*30, " "*5, " "*5, " "*5, " "*20, " "*30 ] ],
    
    indexed_music_file_table = [[
        sg.Table(
            key='indexed-music-file-table',
            headings = [ "Title", "Composer", "Canonical Book Name", "Page", "Sheet", "Src", "Local", "File" ],
            col_widths = [ 20, 10, 20, 4, 4, 3, 10, 20 ],
            values = [],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # default_col_width = 10,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # visible_column_map = [ True, True, True, True, True, True, True, True ],
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,        # if True then num_rows is ignored
          # vertical_scroll_only = False,
        )
    ]]
    
    audio_file_table = [[
        sg.Table(
            key='audio-file-table',
            headings = [ "Title", "Artist", "Album" ],
            col_widths = [ 30, 20, 30 ],
            # visible_column_map = [ True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]
    
    
    youtube_file_table = [[
        sg.Table(
            key='youtube-file-table',
            headings = [ "Title", "YouTube Title", "Duration" ],
            # visible_column_map = [ True, True, True ],
            values = [],
            col_widths = [ 30, 40, 5 ],
            auto_size_columns = False,  # Must be false for col_width to work.
            font=Table_Font,
            row_height = Table_Row_Height,
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]
    
    music_file_table = [[
        sg.Table(
            key='music-filename-table',
            headings = [ "Path", "File"  ],
            # visible_column_map = [ True, True ],
            col_widths = [ 40, 40 ],
            values = [],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # default_col_width = 100,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]

    midi_file_table = [[
        sg.Table(
            key='midi-file-table',
            headings = [ "Path", "File"  ],
            # visible_column_map = [ True, True ],
            col_widths = [ 40, 40 ],
            values = [],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # default_col_width = 100,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]

    chordpro_index_table = [[
        sg.Table(
            key='current-chordpro-table',
            headings = [ "Title", "Artist", "File"  ],
            # visible_column_map = [ True, True, True ],
            col_widths = [ 30, 30, 40 ],
            values = [],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # default_col_width = 100,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]

    jjazzlab_index_table = [[
        sg.Table(
            key='current-jjazz-table',
            headings = [ "Title", "File"  ],
            # visible_column_map = [ True, True ],
            col_widths = [ 40, 40 ],
            values = [],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,  # Must be false for col_width to work.
            justification = 'left',
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # default_col_width = 100,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    ]]

    # --------------------------------------------------------------------------------
    
    set_list_controls = [
        [sg.Combo(
              [],
              key = 'setlist-controls-menu',
              default_value = 'Default',
              font=("Helvetica", 10),
              pad=((8,8),(8,)),
              auto_size_text = True,
              enable_events = True,
              size = 20,
        )],
    
        # [sg.Button('Open', key='setlist-open', font=("Helvetica", 9), pad=((8,8),(0,8)), expand_x = True ) ],
        [sg.Checkbox( 'Edit Setlist', key='setlist-edit', enable_events = True, default=False, auto_size_text=True, font=("Helvetica", 10) )  ],
    
        [sg.Button('Move Up', key='setlist-move-up', disabled = True, font=("Helvetica", 9), pad=((8,8),(0,8)), expand_x = True  ) ],
        [sg.Button('Move Down', key='setlist-move-down', disabled = True, font=("Helvetica", 9), pad=((8,8),(0,8)), expand_x = True  ) ],
        [sg.Button('Delete', key='setlist-delete', disabled = True, font=("Helvetica", 9), pad=((8,8),(0,8)), expand_x = True  ) ],
    
        [sg.Button('Save Setlist', key='setlist-save', font=("Helvetica", 9), pad=((8,8),(0,8)), expand_x = True  ) ],
    ]
    
    setlist_layout = [[
        sg.Table(
            key='setlist-table',
            headings = [ "Title", "Canonical", "File", "Sheet" ],
            col_widths = [ 30, 30, 40, 5 ],
            values = [],
            # visible_column_map = [ True, True, True, True ],
    
            font=Table_Font,
            row_height = Table_Row_Height,
            justification = 'left',
            auto_size_columns = False,  # Must be false for col_width to work.
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            # default_col_width = 100,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        ),
    
        sg.Frame( 'Manage Setlist',
                  set_list_controls,
                  font=("Helvetica", 8),
                  element_justification = 'left',
                  pad = ( (10,10), (10,0) ),
                  vertical_alignment='top' ),
    
    ]]
    
    # --------------------------------------------------------------------------------
    
    results_text = [[
        sg.Multiline( default_text='',
                key='results-text',
                font=("Courier", 10 ),
                write_only = True,
                auto_refresh = True,
                expand_x = True,
                expand_y = True,
        )
    ]]
    
    results_table = [[ sg.Table(
            key='results-table',
            headings = [ "Name", "Value"  ],
            col_widths = [ 50, 50 ],
            # visible_column_map = [ True, True ],
            values = [],
            # font=("Courier", 10 ),
            font=Table_Font,
            row_height = Table_Row_Height,
            justification = 'left',
            auto_size_columns = False,  # Must be false for col_width to work.
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            background_color = Background_Color,
            text_color = Text_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        ) ]]
    
    # --------------------------------------------------------------------
    
    main_menu_definition = [
        ['&File',  [
                    '&Settings::menu-configure',
                    '&Exit::menu-exit',
                   ]
        ],
    #   ['&Edit',  ['&Settings::menu-configure' ]],
        ['&Reports', [
                   'All::menu-stats-all',
                   '----',
                   'Database Stats::menu-stats-database',
                   'Title Count by Src::menu-stats-title-count-src',
                   'Title Count by Src and Canonical::menu-stats-title-count-canon-src',
                   'Title Coverage by Src and Canonical::menu-stats-title-coverage-by-canonical',
                   'Canonical Coverage by Canonical Name::menu-stats-canon-coverage-alpha',
                   'Canonical Coverage by Src Count::menu-stats-canon-coverage-count',
                   'Canonical Names in Canonical Missing in Canonical2File::menu-stats-canon-missing-c2f',
                   'Canonical Names in Local2Canonical Missing in Canonical::menu-stats-canon-missing-l2c',
                   'Canonical Names in Canonical2File Missing in Canonical::menu-stats-c2f-missing-canon',
                   'Files in Canonical2File Missing in Music Library::menu-stats-canon-missing-music',
                   'Top 100 Titles in Music Index::menu-stats-top-forty',
                   ]
        ],
        ['&Database', [
                   'Rebuild All Tables::menu-rebuild-all',
                   'Rebuild Sheet-Offset Table::menu-rebuild-page-offset',
                   'Rebuild Canonical to File Table::menu-rebuild-canon2file',
                 # 'Rebuild Source Priority Table::menu-rebuild-source-priority',
                   'Scan Audio Library (slow for large libraries)::menu-rebuild-audio',
                  ]
        ],

        ['&Index Management', [
                   'Process Raw Index Sources::menu-convert-raw-sources',
                   '----',
                   'Show Page Mismatch and Src Coverage Summary::menu-summary',
                   'Show Page Number Differences Summary::menu-page-summary',
                   'Show Page Mismatch and Src Coverage Detail::menu-verbose',
                    ]
        ],

        [ '&View', [ 
                    'Toggle Index Management Tab::menu-index-mgmt-tabs',
                    'Toggle Edit Canonical->File Tab::menu-canon2file-tab',
                   ]
        ],

        ['&Help',  ['Show Documentation in Music Viewer Tab::menu-tutorial',
                  # 'Show Recent &Log::menu-show-recent-log',
                  # 'Show Recent &Event Histogram::menu-show-recent-event-histo',
                    'Show Birdland Website URL::menu-website',
                    'Contact::menu-contact',
                    '&About Birdland::menu-about',
                  ]
        ]
    ]
    
    # --------------------------------------------------------------------
    #   Width of these is set by max width of pdf_metadata_text_box_size in the first Multiline below
    #       and pdf_display_controls, which is hand tuned by the Sizer element to match the width of these.
    
    control_0 = [
        [   sg.Multiline(
                     # background_color = 'white',
                     # text_color = 'black',
                     key='display-page-title-exp',
                     font=("Helvetica", 11, 'bold'),
                     justification='right',
                     # auto_size_text = True,
                     write_only = True,
                     size = (pdf_metadata_text_box_size, 8),
                     expand_x = True,
                     pad=((3,3), (0,0)),
                     auto_refresh = True,
                     no_scrollbar = False,
                     border_width = 0,
            )
        ],
    ]
    
    control_1 = [
        [   sg.Multiline(
                     # background_color = 'white',
                     # text_color = 'black',
                     key='display-page-local-exp',
                     font=("Helvetica", 10),
                     justification='right',
                     pad=((3,3), (0,0)),
                     # auto_size_text = True,
                     expand_x = True,
                     size = (0, 2),
                     auto_refresh = True,
                     no_scrollbar = True,
                     border_width = 0,
            )
        ],
    ]
    
    control_2 = [
        [   sg.Multiline(
                     # background_color = 'white',
                     # text_color = 'black',
                     key='display-page-canonical-exp',
                     font=("Helvetica", 10, 'bold' ),
                     justification='right',
                     pad=((3,3), (0,0)),
                     # auto_size_text = True,
                     expand_x = True,
                     size = (0, 2),
                     auto_refresh = True,
                     no_scrollbar = True,
                     border_width = 0,
            )
        ],
    ]
    
    control_3 = [
        [   sg.Multiline(
                     # background_color = 'white',
                     # text_color = 'black',
                     key='display-page-file-exp',                                                                                              
                     font=("Helvetica", 10),
                     justification='right',
                     pad=((3,3), (0,0)),
                     # auto_size_text = True,
                     expand_x = True,
                     size = (0, 2),
                     auto_refresh = True,
                     no_scrollbar = True,
                     border_width = 0,
            )
        ],
    ]
    
    pdf_display_metadata = [
        [ sg.Frame( 'Title(s)', control_0, font=("Helvetica", 8), pad=((0,0),(4,4)), expand_x = True ) ] ,
        [ sg.Frame( 'Canonical Name - Publisher', control_2, font=("Helvetica", 8), pad=((0,0),(4,4)), expand_x = True ) ] ,
        [ sg.Frame( 'Local Name - Src', control_1, font=("Helvetica", 8), expand_x = True, pad=((0,0),(4,4)) ) ] ,
        [ sg.Frame( 'Music Filename', control_3, font=("Helvetica", 8), expand_x = True, pad=((0,0),(4,0)) ) ] ,
    ]
    
    pdf_display_controls = [
        [
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/fast-arrow-left.png', border_width=0, key='display-button-first', pad=((4,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/nav-arrow-left.png', border_width=0, key='display-button-prev',  pad=((2,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/nav-arrow-right.png', border_width=0, key='display-button-next',  pad=((2,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/fast-arrow-right.png', border_width=0, key='display-button-last',  pad=((2,0),(4,0)), ),

            sg.Sizer( h_pixels = 32 ),    # Hand tuned for max separation up to size of Multiline boxes (pdf_metadata_text_box_size)

            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/zoom-in.png', border_width=0, key='display-button-zoom-in',  pad=((0,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/zoom-out.png', border_width=0, key='display-button-zoom-out', pad=((2,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/arrow-separate-vertical.png', border_width=0, key='display-button-zoom-height', pad=((2,0),(4,0)), ),
            sg.Button(button_color=sg.TRANSPARENT_BUTTON, image_filename = 'Icons/arrow-separate.png', key='display-button-zoom-width', border_width=0, pad=((2,4),(4,0)), ),
        ],
        [
            sg.Text( text='    ',
                     key='display-page-sheet',
                     font=("Helvetica", 10),
                     justification='left',
                     pad=((4,0), (0,4)),
                     size= int( pdf_metadata_text_box_size/2 + 2),   # extra is hand tuned
            ),

            sg.Text( text='    ',
                     key='display-page-number',
                     font=("Helvetica", 10),
                     justification='right',
                     pad=((0,4),(0, 4)),
                     size= int( pdf_metadata_text_box_size/2 + 3),      # extra is hand tuned
            ),
        ],
    ]
    
    pdf_display_controls_frame = \
        [ sg.Frame( 'Viewer Controls', pdf_display_controls, font=("Helvetica", 8), pad=((0,0),(0,0)), expand_x = True ) ],

    pdf_display_controls_column = \
        sg.Column(
            pdf_display_controls_frame,
            key='display-control-buttons',
          # background_color='#404040',
            vertical_alignment='top',
            # justification='right',
            # element_justification='right',
            # expand_x = False,
            pad=((8,0),(8,0)),
        )
    
    pdf_display_metadata_column = \
        sg.Column(
            pdf_display_metadata,
          # background_color='#404040',
            vertical_alignment='top',
          # justification='left',
          # element_justification='right',
            expand_x = True,
            pad=((8,0),(4,0)),
        )
    
    # hr = sg.HorizontalSeparator()

    pdf_display_sidebar = [ [pdf_display_controls_column], [pdf_display_metadata_column] ]

    pdf_display_sidebar_column = \
        sg.Column(
            pdf_display_sidebar,
            key = 'pdf-display-sidebar',
          # background_color='#404040',
            vertical_alignment='Top',
            justification='left',
            element_justification='right',
            pad=((0,0),(0,0)),
        )
    
    pdf_display_graph = sg.Graph( 
            (400, 400),
            key = 'display-graph-pdf',
            graph_bottom_left=(0, 400),
            graph_top_right=(400,0),
            background_color = GraphBackground,
            pad=((8,0),(14,8)),                     # Must be 8 lower than pdf_display_control_buttons_column
            expand_x = True,
            expand_y = True,
            enable_events = True,
            drag_submits = True,
        )
    
    # Has potential but can't control size, wants to expand horizontally when exapnd_y = True.
    if False:
        pdf_display_slider = sg.Slider(
                range = (1, 100),
                key='display-graph-slider',
                orientation='vertical',
                disable_number_display = True,
                border_width = 0,
                enable_events = True,
                size = (40,10),                      # (Chars/rows, width in pixels)
                pad = ((8,0),(14,8)),
                expand_y = True,
                expand_x = False,
              )

    #   [[ pdf_display_sidebar_column, pdf_display_graph, pdf_display_slider ]]

    display_pdf_layout = \
        [[ pdf_display_sidebar_column, pdf_display_graph ]]
    
    # --------------------------------------------------------------------------------
    #   Index Management

    index_mgmt_info = [

        # -------------------------------
        sg.Text( text='Src: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_mgmt_info_src',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (5, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),

        # -------------------------------

        sg.Text( text='Local: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_mgmt_info_local',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (20, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),


        # -------------------------------

        sg.Text( text='Canonical: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_mgmt_info_canonical',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (40, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),

        # -------------------------------

        sg.Text( text='File: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_mgmt_info_file',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (40, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),

        sg.Text( text='Pages: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_mgmt_info_page_count',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (5, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),
    ]

    index_mgmt_table = \
        sg.Table(
            key='index-mgmt-table',
            headings = [ "Page", "Sheet", "Offset", "Title", "Composer" ],
            col_widths = [ 5, 5, 5, 50, 30 ],
            # visible_column_map = [ True, True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Short_Table_Row_Count,
            pad=[(0, 0), (8, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    
    index_mgmt_src_table = \
        sg.Table(
            key='index-mgmt-src-table',
            headings = [ "Index Source Name" ],
            col_widths = [ 30 ],
            # visible_column_map = [ True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = 8,
            pad=[(10, 0), (8, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    
    index_mgmt_local_table = \
        sg.Table(
            key='index-mgmt-local-table',
            headings = [ "Local Book Name" ],
            col_widths = [ 30 ],
            # visible_column_map = [ True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = 8,
            pad=[(10, 0), (10, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    index_mgmt_open_button = \
        sg.Button('Open Index', key='index-mgmt-open', font=("Helvetica", 9), pad=((8,8),(10,8)), expand_x = False  )

    index_mgmt_column = \
        sg.Column(
            # [[ index_mgmt_src_table], [index_mgmt_local_table], [index_mgmt_open_button ]],
            [[ index_mgmt_src_table], [index_mgmt_local_table]],
          # background_color='#404040',
            vertical_alignment='Top',
            justification='left',
            element_justification='left',
            pad=((0,0),(0,0)),
        )
    
    index_mgmt_layout = [
          index_mgmt_info,
        [ index_mgmt_table, index_mgmt_column ]
    ]

    # --------------------------------------------------------------------------------
    #   Local to Canonical Management

    local2canonical_mgmt_canonical_table = \
        sg.Table(
            key='local2canonical-canonical-mgmt-table',
            headings = [ "All Canonical Names" ],
            col_widths = [ 50 ],
            # visible_column_map = [ True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Short_Table_Row_Count,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            # enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    local2canonical_mgmt_local_table = \
        sg.Table(
            key='local2canonical-local-mgmt-table',
            headings = [ "Local Name", 'Linked Canonical Name' ],
            col_widths = [ 20, 50 ],
            # visible_column_map = [ True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Short_Table_Row_Count,
            pad=[(10, 0), (10, 0)],
            select_mode = None,
            # enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    canon_find_a = [
        sg.Text('Find:', font=search_title_font, pad=((0,4),(11,0))  ),
        sg.InputText( key = 'canon-find-text-a',
                     size=(20,1),
                     font=("Helvetica", 10 ),
                     pad=((0,0),(7,0)),
                     enable_events=True,
                    ),
    ]

    canon_find_b = [
        sg.Text('Find:', font=search_title_font, pad=((0,4),(11,0))  ),
        sg.InputText( key = 'canon-find-text-b',
                     size=(20,1),
                     font=("Helvetica", 10 ),
                     pad=((0,0),(7,0)),
                     enable_events=True,
                    ),
    ]

    src_text = \
        sg.Text( text='Index Src: ',
             font=("Helvetica", 10 ),
             justification='right',
             pad=((10, 4), (14, 0)),
        )

    local2canonical_mgmt_src_combo = \
        sg.Combo(
              [],
              key = 'local2canonical-mgmt-src-combo',
              font=("Helvetica", 10),
              pad=((0,20),(8,0)),
              auto_size_text = True,
              size = 20,
              enable_events = True,
        )

    local2canonical_mgmt_buttons = [
        sg.Button('Link Local to Canonical', key='local2canonical-mgmt-link', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
        sg.Button('Clear One Link', key='local2canonical-mgmt-clear-one', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
        sg.Button('Save', key='local2canonical-mgmt-save', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
        sg.Button('Show Profile for Src/Local', key='local2canonical-mgmt-profile', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
    ]

    l2c_help = \
        sg.Text( text="""Select an index source from the 'Index Src' menu. Select a row in the 'All Canonical Names' table. \
Select a row in the 'Local Name/Linked Canonical Name' table. Click 'Link Local to Canonical'.""",
             font=("Helvetica", 10 ),
             justification='right',
             pad=((10, 0), (4, 0)),
        )

    local2canonical_mgmt_layout = [
        [ src_text, local2canonical_mgmt_src_combo, * local2canonical_mgmt_buttons, *canon_find_a ],
        [l2c_help ],
        [ 
          local2canonical_mgmt_canonical_table,
          local2canonical_mgmt_local_table,
        ]
    ]

    # --------------------------------------------------------------------------------
    #   Canonical to File Management

    canon2file_mgmt_canonical_table = \
        sg.Table(
            key='canon2file-canonical-mgmt-table',
            headings = [ "Canonical Name" ],
            col_widths = [ 40 ],
            # visible_column_map = [ True, True, True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            pad=[(0, 0), (10, 0)],
            select_mode = None,
            # enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    canon2file_mgmt_link_table = \
        sg.Table(
            key='canon2file-link-mgmt-table',
            headings = [ "Canonical Name", 'File Name' ],
            col_widths = [ 40, 40  ],
            visible_column_map = [ True, True ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            # default_col_width = 100,
            # max_col_width = 100,
            num_rows = Table_Row_Count,
            pad=[(10, 0), (10, 0)],
            select_mode = None,
            # enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    canon2file_mgmt_buttons = [
        sg.Button('Link Canonical to File', key='canon2file-mgmt-link', font=("Helvetica", 9), pad=((10,8),(8,0)), expand_x = False ),
        sg.Button('Clear One Link', key='canon2file-mgmt-clear-one', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
        sg.Button('Save', key='canon2file-mgmt-save', font=("Helvetica", 9), pad=((0,8),(8,0)), expand_x = False  ),
    ]

    c2f_help = \
        sg.Text( text="""Select a row in the 'Canonical Name' table. \
Select a row in the 'Canonical Name/Linked File Name' table. Click 'Link Canonical to File'.""",
             font=("Helvetica", 10 ),
             justification='right',
             pad=((10, 0), (4, 0)),
             key = 'c2f-help',
        )

    canon2file_mgmt_layout = [
        [* canon2file_mgmt_buttons, *canon_find_b ],
        [c2f_help ],
        [ 
          canon2file_mgmt_canonical_table,
          canon2file_mgmt_link_table,
        ]
    ]

    # --------------------------------------------------------------------------------
    #   WRW 7 Jan 2022 - Index Diff work. One row/title for all sources
    #   Generate src-specific content dynamically
    #   CURR

    index_diff_info = [
        sg.Text( text='Canonical: ',
             # background_color = 'white',
             # text_color = 'black',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((3,3), (8, 0)),
             # auto_size_text = True,
             # expand_x = True,
             # size=pdf_display_control_text_box_size,
            ),

        sg.Multiline(
            key='index_diff_info_canonical',
            # background_color = 'white',
            # text_color = 'black',
            font=("Helvetica", 10 ),
            justification='left',
            # auto_size_text = True,
            write_only = True,
            size = (40, 1),
            expand_x = False,
            pad=((3,3), (8,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            ),

        sg.Text( text='Notation: ',
             font=("Helvetica", 10, 'bold'),
             justification='right',
             pad=((20,3), (8, 0)),
            ),

        sg.Text( text='Sheet -> Page',
             font=("Helvetica", 10 ),
             justification='right',
             pad=((3,3), (8, 0)),
            ),

        sg.Text( text='Click on column header to show sheet-offset graph.',
             font=("Helvetica", 10 ),
             justification='right',
             pad=((3,3), (8, 0)),
            ),
    ]

    srcs = fb.get_srcs()
    headings = [ "Title", ' M ', *srcs ]
    col_widths = [ 30, 3, *[8 for x in range( 0, len(srcs)) ]]

    index_diff_table = \
        sg.Table(
            key='index-diff-table',
            headings = headings,
            col_widths = col_widths,
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            # values=[values],
            justification = 'left',
            num_rows = Short_Table_Row_Count,
            pad=[(0, 0), (8, 0)],
            select_mode = None,
          # enable_events = True,           # Done later with bind()
          # enable_click_events=True,       # Per Jason for mouse release
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )
    
    index_diff_canonical_table = \
        sg.Table(
            key='index-diff-canonical-table',
            headings = [ "Canonical Book Name, >1 Src" ],
            col_widths = [ 30 ],
            font=Table_Font,
            row_height = Table_Row_Height,
            auto_size_columns = False,     # Must be false for col_width to work.
            values = [],
            justification = 'left',
            num_rows = 10,
            pad=[(10, 0), (8, 0)],
            select_mode = None,
            enable_events = True,
            text_color = Text_Color,
            background_color = Background_Color,
            alternating_row_color= Alternating_Color,
            expand_x = True,
            expand_y = True,
        )

    index_diff_controls_1 = \
        sg.Radio( 'All',
                     'diff-controls',
                     key='index-diff-controls-1', 
                     enable_events = True,
                     default=True,
                     auto_size_text=True,
                     font=("Helvetica", 10),
                     pad=[(8, 0), (0, 0)],
                   )

    index_diff_controls_2 = \
        sg.Radio( 'With Page Mismatches',
                     'diff-controls',
                     key='index-diff-controls-2',
                     enable_events = True,
                     default=False,
                     auto_size_text=True,
                     font=("Helvetica", 10),
                     pad=[(8, 0), (2, 0)],
                   )

    index_diff_controls_3 = \
        sg.Radio( 'With Partial Src Coverage',
                     'diff-controls',
                     key='index-diff-controls-3',
                     enable_events = True,
                     default=False,
                     auto_size_text=True,
                     font=("Helvetica", 10),
                     pad=[(8, 0), (2, 4)],
                   )

    index_diff_edit_titles = \
        sg.Checkbox( 'Enable Select',
                      key='index-diff-edit-titles',
                      enable_events = False,
                      default=False,
                      auto_size_text=True,
                      font=("Helvetica", 10),
                      pad=[(8, 8), (0, 4)],
                      )

    index_diff_select_button = \
        sg.Button( 'Show Select',  key='index-diff-select-button', enable_events = True, font=("Helvetica", 9), pad=((0,0),(0,4)) )

    select_among_similar_controls = \
        [[ index_diff_edit_titles, index_diff_select_button ]]

    show_titles_controls = [
        [ index_diff_controls_1 ],
        [ index_diff_controls_2 ],
        [ index_diff_controls_3 ],
    ]

    select_among_similar_frame = \
        sg.Frame( 'Select One Among Similar Titles', select_among_similar_controls, font=("Helvetica", 8), pad=((8,8),(0,8)), expand_x = True )

    show_titles_frame = \
        sg.Frame( 'Show Titles', show_titles_controls, font=("Helvetica", 8), pad=((8,8),(8,8)), expand_x = True )

    index_diff_column = \
        sg.Column(
            # [[ index_mgmt_src_table], [index_mgmt_local_table], [index_mgmt_open_button ]],
            [
               [ index_diff_canonical_table ],
               [ show_titles_frame ],
               [ select_among_similar_frame ],
            ],

          # background_color='#404040',
            vertical_alignment='Top',
            justification='left',
            element_justification='left',
            pad=((0,0),(0,0)),
        )

    index_diff_layout = [
          index_diff_info,
        [ index_diff_table, index_diff_column ]
    ]

    # --------------------------------------------------------------------------------
    #   WRW 17 Apr 2022 - Finally, and hopefully lastly, tools for creating an index.

    ci_dummy_input = sg.Input(          # Dummy first element to get focus to keep it away from other input boxes.
        key='ci-dummy-input',
        visible=False,
        )

    if False:
        ci_canon_label = sg.Text( text='Canonical:',
             font=("Helvetica", 10 ),
             justification='left',
             pad=((0,0), (10, 0)),
            )

        ci_canon_value = sg.Multiline(
            key='create-index-canonical',
            font=("Helvetica", 10 ),
            justification='left',
            write_only = True,
            size = (40, 1),
            expand_x = False,
            pad=((10,0), (10,0)),
            auto_refresh = True,
            no_scrollbar = True,
            border_width = 0,
            )

    CI_Main_Font_Size = 14
    CI_Main_Button_Size = 12

    ci_title_label = sg.Text( text='Title:',
         font=("Helvetica", CI_Main_Font_Size ),
         justification='left',
         pad=((10,0), (10, 0)),
        )

    ci_title_value = sg.Multiline(
        key='create-index-title',
        font=("Helvetica", CI_Main_Font_Size ),
        justification='left',
        write_only = False,
        size = (30, 2),
        expand_x = False,
        pad=((10,10), (10,0)),
        auto_refresh = True,
        no_scrollbar = True,
        border_width = 0,
        visible = True,
        )

    ci_sheet_label = sg.Text( text='Sheet #:',
         key = 'create-index-sheet-label',
         font=("Helvetica", CI_Main_Font_Size ),
         justification='left',
         pad=((10,0), (10, 0)),
        )

    ci_sheet_value = sg.Input(
        key='create-index-sheet',
        font=("Helvetica", CI_Main_Font_Size ),
        justification='left',
    #   write_only = False,
        size = (5, 1),
        expand_x = False,
        pad=((10,0), (10,0)),
    #   auto_refresh = True,
    #   no_scrollbar = True,
        border_width = 0,
        )

    # ci_experiment_button = sg.Button( 'Ex', key='create-index-experiment', font=("Helvetica", 9), pad=((0,10),(10,10)), expand_x = False  )

    ci_save_button = sg.Button( 'Save', key='create-index-save', font=("Helvetica", CI_Main_Button_Size), pad=((10,0),(15,0)), expand_x = False  )
    ci_save_plus_button = sg.Button( 'Save+', key='create-index-save-plus', font=("Helvetica", CI_Main_Button_Size), pad=((10,0),(15,0)), expand_x = False  )
    ci_skip_button = sg.Button( 'Skip', key='create-index-skip', font=("Helvetica", CI_Main_Button_Size), pad=((10,10),(15,0)), expand_x = False  )

    ci_auto_ocr_switch = \
        sg.Checkbox( 'Auto\nOCR',
                      key='ci-auto-ocr-switch',
                      enable_events = False,
                      default=True,
                      auto_size_text=True,
                      font=("Helvetica", 9),
                      pad=((10,0),(10,10)),
                      )

    ci_title_number_switch = \
        sg.Checkbox( 'Title\nNumber',
                      key='ci-title-number-switch',
                      enable_events = True,
                      default=False,
                      auto_size_text=True,
                      font=("Helvetica", 9),
                      pad=((10,0),(10,10)),
                      )

    ci_delete_button = sg.Button('Delete', key='create-index-delete', font=("Helvetica", 9), pad=((10,0),(10,10)), expand_x = False  )
    ci_update_button = sg.Button('Update', key='create-index-update', font=("Helvetica", 9), pad=((10,0),(10,10)), expand_x = False  )
    ci_show_map_button = sg.Button('Map', key='create-index-show-map', font=("Helvetica", 9), pad=((10,0),(10,10)), expand_x = False  )

    ci_goto_button = sg.Button( 'Go To', 
        key='create-index-goto',
        font=("Helvetica", 9),
        pad=((10,10),(8,8)),
        expand_x = False,
        )

    ci_page_label = sg.Text( text='Page:',
         font=("Helvetica", 10 ),
         justification='left',
         pad=((0,0), (8, 8)),
        )

    ci_page_value = sg.Input(
        key='create-index-page',
        font=("Helvetica", 10 ),
        justification='left',
      # write_only = False,
        size = (5, 1),
        expand_x = False,
        pad=((10,0), (8,8)),
    #   auto_refresh = True,
    #   no_scrollbar = True,
        border_width = 0,
        enable_events = False,
        )

    ci_hrule1 = sg.HorizontalSeparator( color = '#808080' )

    ci_prev_button = sg.Button('Prev', key='create-index-prev', font=("Helvetica", 9), pad=((10,0),(8,8)), expand_x = False  )
    ci_next_button = sg.Button('Next', key='create-index-next', font=("Helvetica", 9), pad=((10,0),(8,8)), expand_x = False  )
    ci_last_button = sg.Button('Last', key='create-index-last-created', font=("Helvetica", 9), pad=((10,10),(8,8)), expand_x = False  )

    ci_graph_size = 350

    ci_pdf_graph = sg.Graph( 
        (ci_graph_size, ci_graph_size),
        key = 'create-index-graph',
        graph_bottom_left=(0, ci_graph_size),
        graph_top_right=(ci_graph_size, 0),
        background_color = GraphBackground,
        pad=((10,0),(10,0)),
        expand_x = True,
        expand_y = True,
        # enable_events = True,           # Both True did not affect Graph focus.
        # drag_submits = True,            # Doing it all with bind() for consistency
    )

    ci_canon_table = sg.Table(
        key='create-index-canonical-table',
        headings = [ f"Canonical Books - {conf.val( 'ci_canon_select' )}" ],
        col_widths = [ 30 ],
        num_rows = 6,
        font=Table_Font,
        row_height = Table_Row_Height,
        auto_size_columns = False,     # Must be false for col_width to work.
        values = [],
        pad=[(0, 0), (10, 0)],
        select_mode = None,
        enable_events = True,
        text_color = Text_Color,
        background_color = Background_Color,
        alternating_row_color= Alternating_Color,
        justification = 'right',
        expand_x = True,
        expand_y = True,
    )

    ci_titles_table = sg.Table(
        key='create-index-review-table',
        headings = [ 'Page', 'Sheet', 'Title' ],
        col_widths = [ 4, 5, 35 ],
        num_rows = 3,
        font=Table_Font_Small,
        row_height = Table_Row_Height_Small,
        auto_size_columns = False,     # Must be false for col_width to work.
        values = [],
        pad=[(8, 8), (4, 8)],
        select_mode = None,
        enable_events = True,
        text_color = Text_Color,
        background_color = Background_Color,
        alternating_row_color= Alternating_Color,
        justification = 'left',
      # hide_vertical_scroll = True,
        expand_x = True,
        expand_y = True,
    )

    ci_main_frame_content = [
        [ ci_title_label, ci_title_value, ],
        [ ci_sheet_label, ci_sheet_value, ci_save_button, ci_save_plus_button, ci_skip_button ],
        [ ci_auto_ocr_switch, ci_title_number_switch, ci_delete_button, ci_update_button, ci_show_map_button ],
        [ ci_titles_table ],
    ]

    ci_main_frame = sg.Frame( 'Create / Edit User Index',
        ci_main_frame_content,
        key = 'create-index-main-frame',
        font=("Helvetica", 8),
        pad=((0,0),(6,0)),
        expand_x = False,
        visible = True,
    )

    ci_nav_frame_content = [
        [ ci_goto_button, ci_page_label, ci_page_value, ci_prev_button, ci_next_button, ci_last_button ],
    ]

    ci_nav_frame = sg.Frame( 'Navigation',
        ci_nav_frame_content,
        key = 'create-index-nav-frame',
        font=("Helvetica", 8),
        pad=((0,0),(6,0)),
        expand_x = True,
        visible = True,
    )

    ci_column_1_content = [
        [ ci_main_frame ],
        [ ci_nav_frame ],
        [ ci_canon_table ],
    ]

    ci_column_1 = sg.Column(
            ci_column_1_content,
            vertical_alignment='Top',
            justification='left',
            element_justification='left',
            pad=((10,0),(0,0)),
        )

    if False:       # Don't need and don't want (caused spacing problems) separate column for canonical table.
        ci_column_2_content = [
            [ ci_canon_table ],
        ]

        ci_column_2 = sg.Column(
                ci_column_2_content,
                vertical_alignment='Top',
                justification='right',
                element_justification='right',
                pad=((8,0),(8,0)),
                expand_y = True,
            )

    create_index_layout = [
        [ci_dummy_input],
        [ ci_column_1, ci_pdf_graph ],
      # [ ci_column_1, ci_pdf_graph, ci_column_2 ],
    ]


    # --------------------------------------------------------------------------------
    #   Layout elements used in frames
    
    search_1 = [[
        sg.Text('Title:', font=search_title_font ),
        sg.InputText( key = 'song-title', size=(20,1), font=("Helvetica", 10 ), background_color='#008000'   ),
    
    ]]
    
    search_2 = [[
        sg.Text('Composer:', font=search_title_font ),
        sg.InputText( key = 'song-composer', size=(15,1), font=("Helvetica", 10 ) ),
    
        sg.Text('Lyricist:', font=search_title_font ),
        sg.InputText( key = 'song-lyricist', size=(15,1), font=("Helvetica", 10 ) ),
    ]]
    
    search_3 = [[
        sg.Text('Artist:', font=search_title_font ),
        sg.InputText( key = 'song-artist', size=(15,1), font=("Helvetica", 10 ) ),
    
        sg.Text('Album:', font=search_title_font ),
        sg.InputText( key = 'song-album', size=(15,1), font=("Helvetica", 10 ) ),
    
        sg.Checkbox( 'Also Search Audio Title in Music', key='search-join-title', default=True, auto_size_text=True, font=("Helvetica", 9) ),
    ]]
    
    search_4 = [[
        sg.Text('Src:', font=search_title_font ),
        sg.InputText( key = 'local-src', size=(5,1), font=("Helvetica", 10 ) ),
    
        sg.Text('Canonical:', font=search_title_font ),
        sg.InputText( key = 'canonical', size=(10,1), font=("Helvetica", 10 ) ),
    ]]
    
    search_5 = [[
        sg.Radio( 'None',           group_id = 'search_5', enable_events = True, key='exclude-duplicate-none',       default=True, auto_size_text=True, font=("Helvetica", 9) ),
        sg.Radio( 'Titles',         group_id = 'search_5', enable_events = True, key='exclude-duplicate-titles',     auto_size_text=True, font=("Helvetica", 9) ),
        sg.Radio( 'Canonicals',     group_id = 'search_5', enable_events = True, key='exclude-duplicate-canonicals', auto_size_text=True, font=("Helvetica", 9) ),
        sg.Radio( 'Srcs',           group_id = 'search_5', enable_events = True, key='exclude-duplicate-srcs',       auto_size_text=True, font=("Helvetica", 9) ),
    ]]
    
    search_6 = [[
        sg.Button('Add',  key='display-button-add-to-setlist', font=("Helvetica", 9), pad=((2,8),(0,0)), ),
        sg.Combo(
              [],
              key = 'setlist-save-menu',
              default_value = 'Default',
              font=("Helvetica", 10),
              pad=((0,2),(0,0)),
              auto_size_text = True,
              size = 20,
        )
    ]]
    
    sidebar_tabgroup_layout = \
        sg.TabGroup( [[
            sg.Tab( ' Browse\n Music ', browse_music_files, key='tab-browse-music-files', font=("Helvetica", 8) ),
            sg.Tab( ' Browse\n Audio ', browse_audio_files, key='tab-browse-audio-files', font=("Helvetica", 8) ),
            sg.Tab( ' Table of\n Contents ', table_of_contents_table,  key='tab-table-of-contents', font=("Helvetica", 8) ),
            sg.Tab( ' Audio of \n Title  \U0001F50a ', current_audio_table,  key='tab-current-audio-table', font=("Helvetica", 8) ),
            sg.Tab( ' Midi of \n Title  \U0001f39d ', current_midi_table,  key='tab-current-midi-table', font=("Helvetica", 8) ),
        ]],
            key='sidebar-tabgroup',
            font=("Helvetica", 9),
            enable_events=True,
            selected_background_color = '#800000',
            pad=((0,8),(0,4)),
            expand_x=False,
            expand_y=True,
         )

    index_mgmt_tabgroup_layout = [[
        sg.TabGroup( [[
            sg.Tab(' Index Comparison ',        index_diff_layout,              key='tab-index-compare', font=Tab_Font ),
            sg.Tab(' Index Page List ',         index_mgmt_layout,              key='tab-index-page-list', font=Tab_Font ),
            sg.Tab(' Create/Edit User Index ',  create_index_layout,            key='tab-create-index', font=Tab_Font ),
            sg.Tab(' Edit Local->Canonical ',   local2canonical_mgmt_layout,    key='tab-local2canon-mgmt', font=Tab_Font ),
        ]],
            key='index-mgmt-tabgroup',
            enable_events=True,
            font=("Helvetica", 10),
            pad=((0,0),(8,0)),
            selected_background_color = '#800000',
            expand_x=True,
            expand_y=True,
        )
    ]]
    
    main_tabgroup_layout = \
        sg.TabGroup( [[
            sg.Tab(' Set List',                 setlist_layout,                 key='tab-setlist-table', font=Tab_Font ),
            sg.Tab(' Music Viewer ',            display_pdf_layout,             key='tab-display-pdf', font=Tab_Font ),
            sg.Tab(' Music Index ',             indexed_music_file_table,       key='tab-indexed-music-file-table', font=Tab_Font ),
            sg.Tab(' Music Files ',             music_file_table,               key='tab-music-filename-table', font=Tab_Font  ),
            sg.Tab(' Audio ',                   audio_file_table,               key='tab-audio-file-table', font=Tab_Font  ),
            sg.Tab(' Midi ',                    midi_file_table,                key='tab-midi-file-table', font=Tab_Font  ),
            sg.Tab(' ChordPro ',                chordpro_index_table,           key='tab-chordpro-index-table', font=Tab_Font  ),
            sg.Tab(' JJazzLab ',                jjazzlab_index_table,           key='tab-jjazzlab-index-table', font=Tab_Font  ),
            sg.Tab(' YouTube ',                 youtube_file_table,             key='tab-youtube-table', font=Tab_Font  ),
            sg.Tab(' Results ',                 results_text,                   key='tab-results-text', font=Tab_Font, visible=False  ),
            sg.Tab(' Results  ',                results_table,                  key='tab-results-table', font=Tab_Font, visible=False ),
            sg.Tab(' Edit Canonical->File ',    canon2file_mgmt_layout,         key='tab-canon2file-mgmt', font=Tab_Font ),
            sg.Tab(' Index Management ',        index_mgmt_tabgroup_layout,     key='tab-mgmt-subtabs', font=Tab_Font ),
        ]],
            key='main-tabgroup',
            enable_events=True,
            font=("Helvetica", 10),
            pad=((0,0),(0,4)),
            selected_background_color = '#800000',
            expand_x=True,
            expand_y=True,
        )

    
    # --------------------------------------------------------------------------------
    #   Build up the layout. Each addition is a horizontal unit.
    
    layout = []
    layout += [[
        hidden_buttons
    ]]
    
    layout += [[
        sg.Menu( main_menu_definition, key='menu-bar', font=("Arial", 10 ),  )         # pad does not appear to be working
        # sg.MenubarCustom( main_menu_definition, key='menu-bar', font=("Helvetica", 10 ),  )                                            
    ]]

    layout += [[
        sg.Image( source=BL_Icon, subsample=2, pad=((8,0),(0,0)) ),

        # sg.Image( source='Icons/Saxophone_128.png', subsample=4),
        # sg.Image( source='Icons/piano-icon.png', subsample=8),
        # sg.Image( source='Icons/Piano-2-red.png', subsample=16),

        sg.Text( Bluebird_Program_Title, pad=((4,0),(4,0)), font=("Helvetica", 20, "bold"), text_color='#e0e0ff', justification='left', expand_x = True ),
      # sg.Text( Bluebird_Program_SubTitle, font=("Helvetica", 10, 'italic', 'bold' ), text_color='#e0e0ff', justification='center', expand_x = True ),
        sg.Text( "\"Let's hear how it goes.\"", pad=((0,0),(6,0)), font=("Times", 18, "italic"), text_color='#e0e0ff', justification='right', expand_x = True ),
      # sg.Image( source= 'Icons/156px-Warning.svg.png', subsample=5, key='warning-icon', visible=False )
    
    ],
    ]
    
#   search_1_tt = """
#   Search Music Index, Audio Index, YouTube Index,  \n\
#   Music Filenames, Midi Filenames.
# """
# , tooltip=search_1_tt

    layout += [[
        sg.Frame( 'Search Indexes, Music/Midi Filenames', search_1, font=("Helvetica", 8) ),
        sg.Frame( 'Search Music Index', search_2, font=("Helvetica", 8) ),
        sg.Frame( 'Search Audio Index for Artist/Album, ChordPro Index for Artist', search_3, font=("Helvetica", 8) ),
    ]]
    
    layout += [[
        sg.Sizer( v_pixels = 8 )
    ]]
    
    layout += [[
        sg.Button('Search', bind_return_key = True, key='search', font=("Helvetica", 9)),
        sg.Button('Clear', key='clear', font=("Helvetica", 9)),
        sg.Button('Stop Audio/Midi/YouTube', key='stop-audio-youtube', font=("Helvetica", 9)),
    #   sg.Button('Stop', key='stop-audio-youtube', font=("Helvetica", 9)),
        sg.Button('Close PDF', key='close-music', font=("Helvetica", 9)),
        sg.Button('Exit', font=("Helvetica", 9)),
    
        sg.Sizer( h_pixels = 10 ),
        sg.Frame( 'Exclude Duplicate', search_5, font=("Helvetica", 8) ),
    
        sg.Sizer( h_pixels = 10 ),
        sg.Frame( 'Filter Music Index By', search_4, font=("Helvetica", 8) ),
    
        sg.Sizer( h_pixels = 10 ),
        sg.Frame( 'Add Title to Setlist', search_6, font=("Helvetica", 8),
            tooltip='Enter name to create new setlist'
         ),
    
    ]]
    
    # layout += [[
    #     sg.HorizontalSeparator( color = 'red' ),
    # ]]
    
    layout += [[
        sg.Sizer( v_pixels = 8 )
    ]]
    
    layout += [[
        sidebar_tabgroup_layout,
        main_tabgroup_layout,
    ]]
    
    layout += [[    #   Unsure why need 'size' but it is needed.
        sg.StatusBar( '',
            key='status-bar',
            size=(1, 1),
            font = ("Helvetica", 10 ),
            pad=((0,0),(0,0)),
            expand_x = True,
            expand_y = True,
        )
    ]]
    
    return layout

# ================================================================================

def set_row_count( n ):
    global Table_Row_Count
    Table_Row_Count = n

def set_row_height( n ):
    global Table_Row_Height
    Table_Row_Height = n

def get_row_height():
    return Table_Row_Height

# --------------------------------------------------------------------------------

if __name__ == '__main__':

    import PySimpleGUI as sg
    import MySQLdb
    import fb_utils
    import PySimpleGUI as sg
    import fb_config

    fb = fb_utils.FB()
    conf = fb_config.Config()
    conf.set_driver( True, False, False )       # Use just MySql for this

    os.chdir( os.path.dirname(os.path.realpath(__file__)))  # Non-operational
    # conf.set_install_cwd( os.getcwd() )

    config = conf.get_config()              # Non-operational
    conf.set_class_variables()

    fb.set_classes( conf )
    fb.set_class_config( )

    conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
    dc = conn.cursor(MySQLdb.cursors.DictCursor)
    
    fb.set_dc( dc )

    window = sg.Window( Bluebird_Program_Title,
                        return_keyboard_events=True,
                        resizable=True,
                       ).Layout( get_layout( sg, fb, conf))

    window.finalize()

    while True:
        event, values = window.Read()

        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break       # Break out of while True main event loop

# --------------------------------------------------------------------------------
