#!/usr/bin/python
# ---------------------------------------------------------------------------
#   WRW 10 Feb 2022 - fb_config.py - Pulled config stuff from fb_utils.py
#       and birdland.py

#   Try migrating away from direct refereces to config and hostname 
#        outside of this module. Done, looks good.

#   WRW 27 Feb 2022 - Convert from configparser to configobj so can include
#       comments and have nested host and source sections. Much cleaner now.
# ---------------------------------------------------------------------------

from pathlib import Path
from configobj import ConfigObj
import shutil
import socket
import json
import sys
import gzip
import subprocess
import os
import re

# ---------------------------------------------------------------------------
#   WRW 2 Jan 2022
#   Build configuration window dynamically. Key must agree with items in the config file.

#   WRW 20 Feb 2022 - Add 'loc' flag to indicate base for value so higher-level functions don't have to
#       have that knowledge, for most options. Works great.

#       loc:
#           '-' - Return val without any change.
#           'a' - Absolute, may include ~user expansion.
#           'c' - Relative to config dir.
#           'C' - Relative to config dir, prefix file name with hostname.
#           'i' - Relative to data directory loaded at installation     
#           's' - Relative to Index_Sources dir under data directory, filename is in data dict, not config file
#           'f' - Relative to Index_Sources dir under data directory.

#       type:
#           'V' - value, textbox
#           'B' - binary, checkbox
#           'C' - multi-value, combobox

#       rows: Number of rows in multiline element in config window.
#             If given, val() returns an array, otherwise a scalar.

#       name: Hard-wired name of file associated with 's' item.

# 'table_row_count' :         { 'type' : 'V', 'show' : True, 'section' : 'System', 'title' : 'Visible number of rows 'type' : 'V', 'show'n in tables' },

#   This really belongs in the Create Index tab but no room for it on small screens.

ci_canon_select = [                 
    'All',                  # Values must agree with selector in fb_create_index.py
    'With No Index',
    'Only With Index',
]

config_data_dict = {
    'music_file_root' :             { 'loc' : 'a', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Root of music files'  },
    'music_file_folders' :          { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing all music files', 'rows' : 5 },
    'c2f_editable_music_folders' :  { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing music files permitting\nCanon->File editing', 'rows' : 2 },
    'audio_file_root' :             { 'loc' : 'a', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Root of audio files'   },
    'audio_folders' :               { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing audio files', 'rows' : 5 },

    'midi_file_root' :              { 'loc' : 'a', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Root of midi files'  },
    'midi_folders' :                { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing midi files', 'rows' : 3  },

    'chordpro_file_root' :          { 'loc' : 'a', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Root of ChordPro files'  },
    'chordpro_folders' :            { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing ChordPro files', 'rows' : 3  },

    'jjazz_file_root' :             { 'loc' : 'a', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Root of JJazzLab files'  },
    'jjazz_folders' :               { 'loc' : '-', 'type' : 'V', 'col' : 'L', 'show' : True, 'section' : 'Host',   'title' : 'Folders containing JJazzLab files', 'rows' : 3  },

    'canonical2file' :              { 'loc' : 'c', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'Host',   'title' : 'Canonical->File map file(s)', 'rows' : 3 },
    'c2f_editable_map' :            { 'loc' : 'c', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'Host',   'title' : 'Editable Canonical->File map file'  },
    'setlistfile' :                 { 'loc' : 'c', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Setlist file' },
    'select_limit' :                { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Maximum number of rows returned' },
    'show_index_mgmt_tabs':         { 'loc' : '-', 'type' : 'B', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Show index management tab' },
    'show_canon2file_tab':          { 'loc' : '-', 'type' : 'B', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Show Edit Canonoical->File tab' },
    'raw_index_editor' :            { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Text Editor for Raw Index'  },
    'raw_index_editor_line_num' :   { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Editor line number option'  },
    'include_titles_missing_file':  { 'loc' : '-', 'type' : 'B', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Include titles missing in music files' },
    'theme':                        { 'loc' : '-', 'type' : 'C', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Theme (restart required)', 'aux1': 'themes' },
    'ci_canon_select':              { 'loc' : '-', 'type' : 'C', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Create Index Canonicals (restart reqd)', 'aux2': ci_canon_select },

    'use_external_music_viewer':    { 'loc' : '-', 'type' : 'B', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Use external music viewer' },
    'external_music_viewer' :       { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'External Music Viewer' },
    'external_audio_player' :       { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'External Audio Player' },
    'external_midi_player' :        { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'External Midi Player' },
    'external_youtube_viewer' :     { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'External YouTube Viewer' },


    #   No user configurable options for these but need them to build conf.v variables.

    'source_priority' :             { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : False, 'section' : 'System', 'title' : 'Src Priority, top is highest', 'rows' : 5  },
    'documentation_dir' :           { 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'music_index_dir' :             { 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'canonicals' :                  { 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'corrections' :                 { 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
  # 'example_canonical2file_source':{ 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'youtube_index' :               { 'loc' : 'i', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'audiofile_index' :             { 'loc' : 'C', 'type' : 'V', 'show' : False, 'section' : 'System' },
  # 'music_file_extensions' :       { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'audio_file_extensions' :       { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'System' },
  # 'index_sources' :               { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'themes' :                      { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'System' },
    'music_from_image' :            { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'System' },

    #   These appear under source-specific sections, e.g. [[Buffalo]]
    #   WRW 5 Mar 2022 - Removed local2canon, sheetoffset, localbooknames. Hard-wired names are fine for these.
    #   Not quite, need definition so can add source directory name. Hard wire filenames here.

    'sheetoffsets' :                { 'loc' : 's', 'type' : 'V', 'show' : False, 'section' : 'Source', 'name' : 'Sheet-Offsets.txt' },
    'local2canon' :                 { 'loc' : 's', 'type' : 'V', 'show' : False, 'section' : 'Source', 'name' : 'Local2Canon.txt' },
    'localbooknames' :              { 'loc' : 's', 'type' : 'V', 'show' : False, 'section' : 'Source', 'name' : 'Local-Book-Names.txt' },
    'folder' :                      { 'loc' : 'f', 'type' : 'V', 'show' : False, 'section' : 'Source' },
    'command' :                     { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'Source' },
    'src' :                         { 'loc' : '-', 'type' : 'V', 'show' : False, 'section' : 'Source' },
}

    #   These are added to config_data_dict only when using MySql.

config_data_dict_mysql = {
    'database_user' :               { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Database User' },
    'database_password' :           { 'loc' : '-', 'type' : 'V', 'col' : 'R', 'show' : True, 'section' : 'System', 'title' : 'Database Password' },
}

# --------------------------------------------------------------------------
#   This contains config variables for reference by others.
#   Reference as: conf.v.config_variable_name where config_variable_name is in table above.

class Var():
     pass

# --------------------------------------------------------------------------
#   WRW 12 Mar 2022 - Dealing with data_directory, location where installation        
#       process places some files. Much cleaner, can remove set_install_cwd() from many locations.
#       Name of self.install_cwd is vestigial.

class Config():

    def __init__( self ):

        self.program_directory = Path( __file__ ).parent.resolve()

        # ------------------------------------------------------------
        #   WRW 16 Mar 2022 - Another approach. No guessing. Packaging places
        #       a file, 'Package_Type_*.txt', identifying the packaging type.

        #   WRW 27 May 2022 - Backing off from all but GitHub. Each has own problems, not worth
        #       the effort to manage multiple package type. GitHub is just about the same as tar
        #       but in a .zip file or as cloned.

        if Path( self.program_directory, 'Package_Type_GitHub.txt' ).is_file():
            self.data_directory = Path( '~/.local/share/birdland/' ).expanduser().as_posix()                                                            
            self.Package_Type = 'GitHub'
        
        elif Path( self.program_directory, 'Package_Type_Tar.txt' ).is_file():
            self.data_directory = Path( '~/.local/share/birdland/' ).expanduser().as_posix()
            self.Package_Type = 'Tar'

        elif Path( self.program_directory, 'Package_Type_Development.txt' ).is_file():
            self.data_directory = self.program_directory.parent.as_posix()
            self.Package_Type = 'Development'

        # elif Path( self.program_directory, 'Package_Type_Setuptools.txt' ).is_file():
        #     self.data_directory = Path( '~/.local/share/birdland/' ).expanduser().as_posix()
        #     self.Package_Type = 'Setuptools'

        # elif Path( self.program_directory, 'src', 'Package_Type_PyInstaller.txt' ).is_file():
        #     self.data_directory = self.program_directory.as_posix()
        #     self.Package_Type = 'PyInstaller'

        # elif Path( self.program_directory, 'Package_Type_Nuitka.txt' ).is_file():
        #     self.data_directory = self.program_directory.as_posix()
        #     self.Package_Type = 'Nuitka'

        # elif Path( self.program_directory, 'Package_Type_Tar.txt' ).is_file():
        #     self.data_directory = Path( '~/.local/share/birdland/' ).expanduser().as_posix()
        #     self.Package_Type = 'Tar'

        else:
            print( f"ERROR-DEV: 'Package_Type_*.txt' file not found at 'fb_config.py' in {self.program_directory}", file=sys.stderr )
            sys.exit(1)

        # print( f"/// fb_config.py: Package_Type: {self.Package_Type}" )

        # ------------------------------------------------------------

        self.install_cwd = self.data_directory                      # Removed set_install_cwd() from calling progs.

        self.confdir = None                                         # ~/.birdland or specified on command line with -c confdir
        self.hostname = socket.gethostname()                        # Only place hostname obtained.
        self.v = Var()                                              # Config options stored under v for use here.
        self.sg = None                                              # Pointer to PySimpleGui.
        self.config = None                                          # Configparser object.
        self.progress = []                                          # Journal of initialization steps for debugging. View with -p option.

        #   Constants. This is (should be :-)) the only place where these values are defined.
        #   All references should obtain values from these.

        # No longer needed self.birdland_version = '0.1 Beta'                                                                       
        self.home_confdir = Path( '~/.birdland' ).expanduser()                  # Home config directory. Always have this for sqlite DB even of another specified.
        self.config_file = 'birdland.conf'                                      # Name of configuration file, in home or specified dir.
        self.index_source_dir = Path( self.data_directory, 'Index-Sources' )    # Root of source-specific directories.
        self.canonical_dir = Path( self.data_directory, 'Canonical' )           # Some additional files

        #   Source-specific files in 'Index-Sources', all hard wired here. All references for the files are to these.
        #   WRW 13 Mar 2022 - Put back in data dict, change 's' below to add name.

        # self.local2canon = 'Local2Canon.txt'
        # self.localbooknames = 'Local-Book-Names.txt'
        # self.sheetoffsets = 'Sheet-Offsets.txt'

        #   Names of both datbases are hard wired.
        #   Choice of which to use, sqlite (default) or mysql, is selected via command line.

        self.mysql_database = 'Birdland'                                                                                                 
        self.sqlite_database = 'Birdland.db'                                                                                             

        #   These are names of default files in the configuration directory created at first launch.

      # self.audiofile_index_file = 'Audio-Index.json.gz'
        self.audiofile_index_file = f"{self.hostname}-Audio-Index.json.gz"
        self.setlist_file = 'setlist.json'                                                                                                    
        self.canonical2file = 'Canonical2File.txt'
      # self.canonical2file = f"{self.hostname}-Canonical2File.txt"
        self.example_canonical2file = 'Example-Canonical2File.txt'

    # ----------------------------------------------------------------------------

    def set_classes( self, sg, fb ):
        self.sg = sg
        self.fb = fb

    # ----------------------------------------------------------------------------
    #   WRW 23 Feb 2022 - Removed set_cwd(). Original idea was to find config file
    #       in directory where launched, which is not necessairly the install directory.
    #       No longer interested in that and this was being used incorrectly to indicate
    #       the install directory. Now sett install dir explicitly in calling programs.

    #   WRW 12 Mar 2022 - With exploration of installation issues it looks like this is a bad
    #       idea. install_cwd is only used for a few files. Let's ignore set_install_cwd() and instead
    #       use a directory set depending on the type of installation. Details later.

    # def set_cwd( self, cwd ):
    #     self.cwd = cwd

    # def set_install_cwd( self, cwd ):
    #     # self.install_cwd = cwd
    #     # self.install_cwd = self.data_directory
    #     pass

    # ----------------------------------------------------------------------------
    #   Set driver to modify the data dictionary.

    def set_driver( self, t1, t2, t3 ):
        global MYSQL, SQLITE, FULLTEXT

        MYSQL = t1
        SQLITE = t2
        FULLTEXT = t3

        if MYSQL:
            config_data_dict.update( config_data_dict_mysql )

    # ----------------------------------------------------------------------------

    def set_icon( self, icon ):
        global BL_Icon
        BL_Icon = icon

    # ----------------------------------------------------------------------------
    #   Accessor function for configuration options.
    #   WRW 20 Feb 2022 - Trying to insulate calling code further from configuration details.
    #       This will fetch the config value indicated by item and possibly expanded as indicated by 'loc' flag.
    #       For now convert all to posix. Later may want to deal only with Path.
    #       If 'rows' is defined return values as list, otherwise as a single value.
    #   WRW 21 Feb 2022 - add 'src' argument to get source-specific options.

    def val( self, item, source=None ):
        if item not in config_data_dict:
            print( f"ERROR-DEV, configuration item {item} not in data dictionary", file=sys.stderr )
            sys.exit(1)

        # ---------------------------------------------------------------
        #   Get val from source-specific section of config.
        #   Have to go back to configparser object to handle this. 
        #   Assume loc is '-' for this. That is the case for all items so far.

        if source:
            # if not self.config.has_section( source ):
            if not 'Source' in self.config and source not in self.config[ 'Source' ]:
                print( f"ERROR-DEV, Source {source} section not found in config file {self.config_file}", file=sys.stderr )
                sys.exit( 1 )

            dd = config_data_dict[ item ]
            if dd[ 'section' ] != 'Source':
                print( f"ERROR-DEV, configuration item {item} does not match 'Source' section in config file {self.config_file}", file=sys.stderr )
                sys.exit( 1 )

            # val = self.config['Source'][ source ][ item ]
            loc = dd[ 'loc' ]

            if loc == '-':
                val = self.config['Source'][ source ][ item ]
                return val

            elif loc == 's':
                name= dd[ 'name' ]
                return Path( self.install_cwd, "Index-Sources", source, name )

            elif loc == 'f':
                val = self.config['Source'][ source ][ item ]
                return Path( self.install_cwd, "Index-Sources", val )

        # ----------------------------------------------------------------
        #   WRW 5 Mar 2022 - Looks like issue here when have empty val. Introduced that 
        #       in the host-specific values in the config file initialized here.
        #       No, working just as expected. For 'c' returned just confdir without any file.
        #   WRW 16 May 2022 - add test for empty val so don't return [''] or PosixPath( '.' )

        dd = config_data_dict[ item ]
        val = getattr( self.v, item )
        loc = dd[ 'loc' ]

        rows = dd[ 'rows' ] if 'rows' in dd else None

        if loc == '-':
            if val:
                return [ x for x in val.split( '\n' ) ] if rows else val
            else:
                return [] if rows else val

        elif loc == 'c':
            if val:
                return [ Path( self.confdir, x ).as_posix() for x in val.split( '\n' ) ] if rows else Path( self.confdir, val ).as_posix()
            else:
                return [] if rows else ''

        # WRW 4 Mar 2022 - Add hostname to filename.
        #   I'd rather put it between stem and suffixes but a general solution too much work and this is fine.

        elif loc == 'C':    
            if val:
                if rows:
                    res = []
                    for x in val.split( '\n' ):
                        res.append( Path( self.confdir, f"{self.hostname}-{x}" ).as_posix() )
                    return res
                else:
                    t = Path( self.confdir, f"{self.hostname}-{val}" ).as_posix()
                    return t
            else:
                return [] if rows else ''

        elif loc == 'i':
            if val:
                return [ Path( self.install_cwd, x ).as_posix() for x in val.split( '\n' ) ] if rows else Path( self.install_cwd, val ).as_posix()
            else:
                return [] if rows else ''

        elif loc == 'a':
            if val:
                return [ Path( x ).expanduser().as_posix() for x in val.split( '\n' ) ] if rows else Path( val ).expanduser().as_posix()
            else:
                return [] if rows else ''

        elif loc == 's' or loc == 'f':        # Used only when source specified.
            pass

        else:
            print( f"ERROR-DEV, unexpected 'loc' value '{loc} for {item} in data dictionary", file=sys.stderr )
            sys.exit(1)

    # ----------------------------------------------------------------------------
    #   WRW 5 March 2022 - needed this when removed 's' items from data dict.

    def get_source_path( self, source ):
        # return Path( self.install_cwd, "../Index-Sources", source )
        return Path( self.install_cwd, "Index-Sources", source )

    # ----------------------------------------------------------------------------
    #   WRW 5 March 2022 - Get an array of all source sections in config file.

    def get_sources( self ):
        return self.sources

    # ----------------------------------------------------------------------------
    #   I got tired of the text for popup cluttering up the code with content at the left margin.

    def do_popup( self, txt ):
        txt = re.sub( ' +', ' ', txt )
        txt = re.sub( '\n ', '\n', txt )          # Remove space at beginning of line
        t = self.do_popup_raw( txt )
        return t

    def do_popup_raw( self, txt, font=("Helvetica", 10 ) ):                # No space removal, preserve txt as is.
        t = self.sg.popup( txt,
            title='Birdland Notice',
            font=font,
            icon=BL_Icon,
            line_width = 200,
            keep_on_top = True,
        )
        return t

    def do_popup_ok_cancel( self, txt ):
        txt = re.sub( ' +', ' ', txt )
        txt = re.sub( '\n ', '\n', txt )          # Remove space at betinning of line
        t = self.sg.popup_ok_cancel( txt,
            title='Birdland Notice',
            font=("Helvetica", 10 ),
            icon=BL_Icon,
            line_width = 200,
            keep_on_top = True,
        )
        return t

    def do_nastygram( self, option, path ):
        if not option in config_data_dict:
            print( f"ERROR-DEV: option {option} not found in config_data_dict", file=sys.stderr )
            sys.exit(1)

        title = config_data_dict[ option ][ 'title' ]
        t = f"""It appears that you have not configured the\n
            \t'{title}'\n
            option or the location\n
            \t'{path}' is not a full path to a file.\n
            Please update your settings: 'File->Settings'.
        """
        self.do_popup( t )
        return

    # --------------------------------------------------------------------------
    #   Look for config directory and file in one, not several, well-known locations unless specified
    #       by user. Creat it in default location if not found.
    #       Save config filename and config dir for possible later use by save_config()
    #   Configuration is saved in class variables in self.v object for reference elsewhere.
    #   Note that raw 'config' as returned by configparser is not used externally.

    #   WRW 22 Feb 2022 (Yes, 22222) - I don't think I should be trying to initialize here.
    #       Do that separately. Getting into a loop when build-table.py calls get_config() when
    #       we call build-table.py here to build the table. Pulled it out.

    def get_config( self, confdir=None ):
        if confdir:     
            path = Path( confdir, self.config_file )
            self.confdir = Path( confdir )

        else:    
            path = Path( self.home_confdir, self.config_file )          # Config file not specified, use home_config.
            self.confdir = self.home_confdir

        self.config_file = path

        #   WRW - Had to add as_posix() when running in virtual environment???

        self.config = ConfigObj( path.as_posix() )                 # *** Bang! Read config file here.

        # ----------------------------------------------------------------

        return self.config

    # ------------------------------------------------------------------------
    #   Set class variables for later access. For migration away from hostname and direct references.
    #   Get source names from config file and a map to the src names, which must be an element of the source.

    def set_class_variables( self ):

        config = self.config

        # --------------------------------------------------
        #   WRW 2 Mar 2022 - Finally geting around to localizing the definition of the source/src to just
        #   the config file (and probably the source-specific routines do_*.py in Index-Sources). They
        #   must agree with the config file.

        self.sources = config[ 'Source' ].sections
        self.source_to_src = {}
        self.src_to_source = {}

        for source in self.sources:
            if 'src' not in config[ 'Source' ][ source ]:
                print( f"ERROR: At set_class_variables() config file {self.config_file} missing 'src' for {source} in 'Source' section" )
                sys.exit(1)

            ssource = str( source )

            src = str( config[ 'Source' ][ source ][ 'src' ] )
            self.source_to_src[ ssource ] = src
            self.src_to_source[ src ] = ssource

        # --------------------------------------------------
        #   Populate self.v for access by val()

        for item, dd in config_data_dict.items():                                                

            # -----------------------------------------
            try:
                if dd[ 'section' ] == 'Host':
                    val = config['Host'][ self.hostname ][ item ]

                elif dd[ 'section' ] == 'System':
                    val = config[ dd['section'] ][ item ]

            except KeyError as e:
                if self.sg:
                    self.sg.popup( f"\n\nYour configuration file in {self.confdir} is missing {e}\n\n",
                        title='Birdland Error',
                        font=("Helvetica", 10 ),
                        icon=BL_Icon,
                        line_width = 100,
                        keep_on_top = True,
                    )
                    sys.exit(1)

                else:
                    print( f"ERROR Your configuration file in {self.confdir} is missing {e}", file=sys.stderr )
                    sys.exit(1)

            if dd[ 'type' ] == 'B':                                                       
                val = True if val == 'True' else False
            setattr( self.v, item, val )

            # -----------------------------------------

    # ============================================================================
    #   Display configuration window so user can change settings.
    
    # def do_configure( self, first=None, confdir=None, text=None ):

    def do_configure( self, **kwargs ):
        first =   kwargs[ 'first' ]   if 'first'   in kwargs else False
        confdir = kwargs[ 'confdir' ] if 'confdir' in kwargs else None
        text =    kwargs[ 'text' ]    if 'text'    in kwargs else None
    
        config = self.get_config( confdir )
        user_input_font = ("Helvetica", 9 )
    
        config_layout = []
        layout_left = []
        layout_right = []

        # --------------------------------------------------------------------------
        t = [self.sg.Text( '',
            key = 'first-time-message',
            font=("Helvetica", 10),
            pad=( (8,8), (10,10) ),
            size = (120, 10 ),
            # no_scrollbar = True,
            expand_y = False,
            expand_x = False,           # With True the text was centered.
            visible = False,
            justification='left',
            # text_color = '#000000',
            # background_color = '#e0e0ff',
        )]
        config_layout.append( t )

        #   A little eye candy but can't make it invisible when not needed.
        # t = [ self.sg.HorizontalSeparator(
        #     key = 'first-time-message-rule',
        #     pad = ((8,8),(0,10)),
        #     )
        # ]
        # config_layout.append( t )

        # --------------------------------------------------------------------------
        #   Traverse config_data_dict to build configuration user interface.

        text_line_size = 35

        for item, dd in config_data_dict.items():       # Build configuration layout for dd items
            if not dd[ 'show' ]:
                continue
    
            if dd[ 'section' ] == 'Host':
                val = config['Host'][ self.hostname ][ item ]
            else:
                val = config[ dd['section'] ][ item ]
    
            # -------------------------
            if 'title' in dd:
                title = dd[ 'title' ]
            else:
                title = item
    
            # -------------------------
            if dd[ 'type' ] == 'V':

                if 'rows' in dd:
                    rows = dd[ 'rows' ]
                    no_scrollbar = False
                else:
                    rows = 1
                    no_scrollbar = True

                # -------------------------
                line = [
                    self.sg.Text( title, size=(text_line_size, 1), justification='right', pad=((4,4),(8,0)), expand_y = True ),
                    self.sg.Multiline(
                        size = ( 30, rows ),
                        font=user_input_font,
                        default_text=val,
                        expand_x = True,
                        auto_size_text = True,
                        no_scrollbar = no_scrollbar,
                        key = item,
                        pad=((4,4),(8,0)),
                    )
                ]
    
            # -------------------------
            #   Binary checkbox

            elif dd[ 'type' ] == 'B':

                t = True if val == 'True' else False

                line = [
                    self.sg.Text( title, size=(text_line_size, 1), justification='right' ),
                    self.sg.Checkbox( '', key=item, default=t, auto_size_text=True, font=("Helvetica", 9), pad=((4,4),(8,0))   ),
                ]

            # -------------------------
            #   Combo box, values come from 'aux1' or 'aux2'

            elif dd[ 'type' ] == 'C':
                if 'aux1' in dd:
                    content = [ x for x in config[ dd['section'] ][ dd['aux1'] ].split('\n' )]

                elif 'aux2' in dd:
                    content = dd['aux2']  

                line = [
                    self.sg.Text( title, size=(text_line_size, 1), justification='right' ),
                    self.sg.Combo( content,
                        font=user_input_font,
                        default_value=val,
                        key = item,
                        pad=((4,4),(8,0)),
                    )
                ]

            if dd['col'] == 'L':
                layout_left.append( line )
            else:
                layout_right.append( line )
    
        # --------------------------------------------------------------------------

        config_column_left = \
            self.sg.Column(
                layout_left,
                key='config-column-left',
              # background_color='#404040',
                vertical_alignment='top',
                # justification='left',
                # element_justification='right',
                pad=((8,0),(6,0)),
            )

        config_column_right= \
            self.sg.Column(
                layout_right,
                key='config-column-right',
              # background_color='#404040',
                vertical_alignment='top',
                # justification='right',
                # element_justification='right',
                pad=((8,0),(6,0)),
            )

        config_columns = [ config_column_left, config_column_right ]

        config_layout.append( config_columns )

        # --------------------------------------------------------------------------
        #   Add Cancel and Save buttons to layout                 
    
        b1 = self.sg.Button('Cancel', key='config-button-cancel', font=("Helvetica", 9), pad=((2,2),(2,1)), )
        b2 = self.sg.Button('Save',  key='config-button-save',  font=("Helvetica", 9), pad=((2,2),(2,1)), )
    
        config_layout.append( [b1, b2] )
    
        # --------------------------------------------------------------------------
        #   Finally, show window.

        config_window = self.sg.Window( 'Birdland Settings',
                            return_keyboard_events=False,
                            resizable=True,
                            icon=BL_Icon,
                            finalize = True,
                            text_justification = 'left',        # Not working
                            layout=config_layout,
                            keep_on_top = True,
                           )
    
        if first:   # Show message already in layout on first run.
            if text:
                config_window[ 'first-time-message' ].update( text )

            config_window[ 'first-time-message' ].update( visible=True )

            # config_window[ 'first-time-message' ].update( visible=False )
            # config_window[ 'first-time-message-rule' ].update( visible=True )
    
        # --------------------------------------------------------------------------
        #   EVENT Loop for settings (configuration) window.
    
        while True:
            event, values = config_window.Read( )
    
            if event == self.sg.WINDOW_CLOSED:
                return False
    
            elif event == 'config-button-cancel':
                config_window.close()
                return False
    
            elif event == 'config-button-save':
                if self.validate_config( values ):
                    config = self.do_configure_save( config, values )
                    config_window.close()
                    self.get_config( confdir )               # Reread the saved config
                    self.set_class_variables()
                    return True

                else:
                    t = "One or more settings are not valid:\n\n"
                    t += '\n'.join( self.validate_errors )
                    t += '\n'
                    self.do_popup( t )

    # --------------------------------------------------------------------------
    #   WRW 26 Feb 2022 - Add code to validate some configuration values before
    #       save config back in birdland.conf.

    def validate_config( self, values ):
        errors = []

        for folder in values[ 'music_file_folders' ].split( '\n' ):
            path = Path( Path( values[ 'music_file_root' ] ).expanduser(), folder )
            if not path.is_dir():
                errors.append( f"Music folder '{path}' not found." )

        for folder in values[ 'audio_folders' ].split( '\n' ):
            path = Path( Path( values[ 'audio_file_root' ] ).expanduser(), folder )
            if not path.is_dir():
                errors.append( f"Audio folder '{path}' not found." )

        for folder in values[ 'midi_folders' ].split( '\n' ):
            path = Path( Path( values[ 'midi_file_root' ]).expanduser(), folder )
            if not path.is_dir():
                errors.append( f"Midi folder '{path}' not found." )

        if MYSQL and values[ 'database_user' ] and values[ 'database_password' ]:
            import MySQLdb
            try:
                conn = MySQLdb.connect( "localhost", values[ 'database_user' ] , values[ 'database_password'], self.mysql_database )

            except Exception as e:
                (extype, exvalue, traceback) = sys.exc_info()
                errors.append( f"Error accessing {self.mysql_database} database:" )
                errors.append( f"\t{exvalue}" )         # This is not as pretty.
                # errors.append( f"\t{e.args[1]}" )     # This assumes execpetion-specific knowledge.

            else:
                conn.close()

        self.validate_errors = errors

        return False if len( errors ) else True
    
    # --------------------------------------------------------------------------

    def do_configure_save( self, config, values ):
    
        # -------------------------------------------------------------
        #   Copy parameters in configure window back into the config
        #       and save it
    
        for item, dd in config_data_dict.items():
            if not dd[ 'show' ]:
                continue

            val = values[ item ]
            # print( f"item: {item}, val: {val}, dd: {dd}" )

            if dd[ 'type' ] == 'B':
                val = 'True' if val else 'False'

            if dd[ 'section' ] == 'Host':
                config['Host'][ self.hostname ][ item ] = val
            else:
                config[ dd['section'] ][ item ] = val

        self.save_config( config )
        return config
    
    # --------------------------------------------------------------------------
    #   Backup current config file and save config in config file.

    def save_config( self, config, config_file = None ):        # config_file only used when testing fb_utils in __main__.
        if not config_file:
            config_file = Path( self.config_file )

        backup_file = Path( config_file.parent, config_file.name + '.bak' )
        backup_path = Path( self.confdir, backup_file ).as_posix()
        config_path = Path( self.confdir, config_file ).as_posix()

        if Path(config_path).is_file():           # Possibly nothing to backup
            shutil.copyfile( config_path, backup_path )

        config.filename = config_path
        config.write()

        # with open( config_path, "w" ) as fo:
        #     config.write( fo  )

    # ==========================================================================
    #   WRW 23 Feb 2022 - After a frustrating afternoon yesterday trying to figure out the best
    #       structure for initial launch I decided to break out checking from building.
    #       build-tables.py will check and not even try to run if configuration not set up.
    #       This assumes we will definitely need the home config directory. If using MySql that may
    #       not be the case but for now keep it. I'll likely eventually put other files in there, too.
    #   WRW 24 Feb 2022 - Another frustrating day, too tired. Split out home check and build.

    #   Check if ~/.birdland exists
    #   Check if ~/.birdland/birdland.conf exists if confdir not specified on command line.

    def check_home_config( self, confdir=None ):
        results = []
        success = True

        if not self.home_confdir.is_dir():
            results.append( f"ERROR: Home configuration directory '{self.home_confdir}' not found" )
            success = False

        if not confdir:
            if not Path( self.home_confdir, self.config_file ).is_file():
                results.append( f"ERROR: Configuration file '{self.config_file}' not found in {self.home_confdir}" )
                success = False

        return results, success

    # --------------------------------------------------------------------------
    #   WRW 7 Mar 2022 - In a pathological case some files were missing. Let's catch
    #       them and report with a sensible error message.

    def check_confdir_content( self ):
        results = []
        success = True
        confdir = self.confdir

        path = Path( confdir, self.config_file )
        if not path.is_file():      # A safety check. Don't creat one if already exists. Don't want to overwrite.
            results.append( f"ERROR {path} not found" )
            success = False

        path = Path( confdir, self.setlist_file ).expanduser()
        if not path.is_file():
            results.append( f"ERROR {path} not found" )
            success = False
               
      # path = Path( confdir, f"{self.hostname}-{self.audiofile_index_file}" ).expanduser()
        path = Path( confdir, self.val( 'audiofile_index' ))
        if not path.is_file():
            results.append( f"ERROR {path} not found" )
            success = False

        for file in self.val( 'canonical2file' ):
            path = Path( confdir, file )
            if not path.is_file():
                results.append( f"ERROR {path} not found" )
                success = False

        return results, success

    # --------------------------------------------------------------------------
    #   Check if confdir exists if confdir specified.
    #   Check if birdland.conf exists in confdir if confdir specified.
    #   Check if ~/.birdland/birdland.conf exists if confdir not specified on command line. No, removed.

    def check_specified_config( self, confdir=None ):
        results = []
        success = True

        if confdir:
            if not Path( confdir ).is_dir():
                results.append( f"ERROR: Specified configuration directory '{confdir}' not found" )
                success = False

            if not Path( confdir, self.config_file ).is_file():
                results.append( f"ERROR: Configuration file {self.config_file} not found in specified configuration directory '{confdir}'" )
                success = False

        # if not confdir:
        #     if not Path( self.home_confdir, self.config_file ).is_file():
        #         results.append( f"ERROR: Configuration file {self.config_file} not found in home configuration directory '{self.home_confdir}'" )
        #         success = False

        return results, success

    # --------------------------------------------------------------------------
    #   Check for existence of [[Host]] [hostname] section in config file. This called after
    #   config loaded by get_config() so have conf.confdir defined.
    #   Check number of [hostname] sections to see if already initialized at least once.

    def check_hostname_config( self ):
        results = []
        success = True

        if not self.hostname in self.config['Host']:
            results.append( f"ERROR: Hostname {self.hostname} not found in 'Host' section of configuration file" )
            success = False

        return results, success

    # --------------------------------------------------------------------------
    #   Check if .birdland/birdland.db exists if SQLITE.
    #   Check if can connect to mysql database if MYSQL.

    def check_database( self, database='' ):
        results = []
        success = True

        if SQLITE and database == 'sqlite':
            if not Path( self.home_confdir, self.sqlite_database ).is_file():
                results.append( f"ERROR: Database file {self.sqlite_database} not found in home configuration directory '{self.home_confdir}'" )
                success = False

        if MYSQL and database == 'mysql':
            import MySQLdb
            try:
                conn = MySQLdb.connect( "localhost", self.val( 'database_user' ), self.val( 'database_password' ), self.mysql_database  )

            except Exception as e:
                (extype, value, traceback) = sys.exc_info()
                results.append( f"ERROR: Connect to MySql database {self.mysql_database} failed, type: {extype}, value: {value}" )
                success = False
            else:
                conn.close()

        return results, success

    # --------------------------------------------------------------------------
    #   WRW 6 Mar 2022 - Make [[Host]] [hostname] section for current hostname from ProtoHostnameSection.
    #   No doing it in all initialization cases.          
    #   Motivated by circumstance when Birdland run and config initalized
    #       on one machine in a shared confdir and then run on another machine
    #       with with the same shared confdir. Need a different [hostname] section
    #       for each new machine.

    def initialize_hostname_config( self ):

        if len( self.config['Host'].keys() ) == 1:
            first_config = True
        else:
            first_config = False
            prior_hosts = ', '.join( self.config['Host'].keys()[1:] )

        proto_config =   self.config[ 'Host' ][ 'ProtoHostnameSection' ]
        proto_comments = self.config[ 'Host' ][ 'ProtoHostnameSection' ].comments

        self.config[ 'Host' ][ self.hostname ] = { tag : proto_config[ tag ] for tag in proto_config }
        self.config[ 'Host' ][ self.hostname ].comments = { tag : proto_comments[ tag ] for tag in proto_comments }

        # ----------------------------------------
        #   /// RESUME OK - Cosmetics, add couple of blank lines in config file.
        #   Trying to add a couple of blank lines above the hostname section but this makes save_config() crap out.
        #       self.config[ 'Host' ].comments = {
        #           self.hostname : [ '', '' ],
        #       }
        # ----------------------------------------

        self.save_config( self.config )

        t = ''

        if not first_config:
            t = f"""\nThis appears to be the first time you launched Birdland on     
                    {self.hostname} using a shared configuration directory that had 
                    been previously initialized on {prior_hosts}.
                """

        t += f"""Added a section for this host '{self.hostname}' to the configuration file.
                 \nPlease enter configuration details for this host with 'File->Settings'.
            """
        self.progress.append( t )

    # ----------------------------------------------------------------------------
    #   WRW 24 Feb 2022 - Pulled this out of initialize_config(). Called from birdland.py when it
    #       recognizes the configuration is missing.
    #   If ~/.birdland does not exist:
    #       Create ~/.birdland 
    #       Initialize ~/.birdland content if confdir not specified.

    def initialize_home_config( self, confdir=None ):
        path = self.home_confdir  
        if not path.is_dir():
            if path.is_file():
                self.do_popup( f"""\nERROR: A file with the same name as the home configuration directory {self.home_confdir} already exists.\n
                                 Click OK to exit.\n""" )
                sys.exit(1)

            self.progress.append( 
                f"""\nThis appears to be the first time you launched Birdland.
                    Creating the home configuration directory '{path}' and initial content.""" )

            path.mkdir()
            if not confdir:
                self.initialize_config_directory( self.home_confdir )

        # ---------------------------------------------------------------------------------------------------
        # Have home config directory but it may not have been initialized if first ran with specified confdir and
        #   now ran without specified confdir.

        else:
            if not confdir:
                if not Path( self.home_confdir, self.config_file ).is_file():
                    self.progress.append( f"""\nThis appears to be the first time you launched Birdland without a config directory specified on the command line.""" )
                    self.progress.append( f"""Adding initial content to the home configuration directory.""" )

                    self.initialize_config_directory( self.home_confdir )

    # --------------------------------------------------------------------------
    #   WRW 24 Feb 2022 - Initalize the specified confdir.

    #   If specified config directory does not exist:
    #       Make specified configuraion directory.
    #       Initialize specified directory content

    def initialize_specified_config( self, confdir ):

        # ------------------------------------------------------
        # User specified configuration directory. Create and initialize if doesn't exist.

        if confdir:     
            path = Path( confdir )
            if not path.is_dir():
                if path.is_file():
                    self.do_popup( f"""\nERROR: A file with the same name as the specified configuration directory {confdir} already exists.\n
                        Click OK to exit.\n""" )
                    sys.exit(1)

                self.progress.append(
                f"""\nThis appears to be the first time you launched Birdland with the configuration directory '{confdir}'
                    specified on the command line. Creating the specified configuration directory and initial content.""" )

                path.mkdir()
                self.initialize_config_directory( confdir )

            else:
                print( "ERROR: Found specified configuration directory when none expected" )
                sys.exit(1)

        # ------------------------------------------------------
        #   User did NOT specify config directory, make it in home directory, which was already initialized
        #       by initialize_home_config() above.

        # else:
        #     path = Path( self.home_confdir, self.config_file )          # Config file not specified, use home_config.
        #     self.initalize_config_directory( self.home_confdir )

    # ----------------------------------------------------------------------------
    #   Copy or initialize several files, including birdland.conf, into configuration directory.

    def initialize_config_directory( self, confdir ):

        self.progress.append( '' )

        # ----------------------------------------------------------
        #   Initialize config file with default settings.
        #   WRW 3 Mar 2022 - Now build a new config file from the proto config file.
        #       Originally it was built with a simple copy:
        #           config_file_path.write_text(  Path( default_proto_file_name  ).read_text() )                                

        defconfig = ConfigObj( 'birdland.conf.proto'  )      # *** Hard wired filename specified here.
        config_file_path = Path( confdir, self.config_file )

        if not config_file_path.is_file():      # A safety check. Don't creat one if already exists. Don't want to overwrite.
            defconfig.filename = config_file_path
            defconfig.write()
            self.progress.append( f"Created initial configuration file: {config_file_path}" )

        # ----------------------------------------------------------
        #   Initialize setlist

        setlist_path = Path( confdir, self.setlist_file ).expanduser()
        if not setlist_path.is_file():
            t = { 'current' : 'Default', 'setlist' : [] }
            setlist_path.write_text( json.dumps( t, indent=2 ) )
            self.progress.append( f"Created empty setlist file: {setlist_path}" )
               
        # ----------------------------------------------------------
        #   Initialize audio index.
        #   This failed: audio_index_path.write_bytes( gzip.compress( json.dumps( t, indent=2 )) )

        audio_index_path = Path( confdir, self.audiofile_index_file )
        if not audio_index_path.is_file():
            t = { 'audio_files' : [] }
            json_text = json.dumps( t, indent=2 )
            with gzip.open( audio_index_path, 'wt' ) as ofd:
                ofd.write( json_text )
            self.progress.append( f"Created empty audio index file: {audio_index_path}" )

        # ----------------------------------------------------------
        #   Initialize canonical2file for user to populate.                       

        canonical2file_path = Path( confdir, self.canonical2file )
        if not canonical2file_path.is_file():
            Path.touch( canonical2file_path )
            self.progress.append( f"Created empty canonical2file file: {canonical2file_path}" )

        # ----------------------------------------------------------
        #   Copy example canonical2file for user.

        example_canonical2file_dest_path = Path( confdir, self.example_canonical2file )
        if not example_canonical2file_dest_path.is_file():

            example_canonical2file_dest_path.write_text( Path( self.canonical_dir, self.example_canonical2file ).read_text() )

            self.progress.append( f"Copied example canonical2file file: {example_canonical2file_dest_path}" )

    # ----------------------------------------------------------------------------
    #   Pulled out of above.

    def report_progress( self ):

        self.progress.append( f"""Click OK to continue.\n""" )

        txt = '\n'.join( self.progress )        # Make string out of list of strings
        txt = re.sub( ' +', ' ', txt )          # Collapse multiple spaces into one.
        txt = re.sub( '\n ', '\n', txt )        # Remove space at betinning of line

        self.sg.popup( txt,
            title='Birdland Notice',
            font=("Helvetica", 10 ),
            icon=BL_Icon,
            line_width = 200,
            keep_on_top = True,
        )

    # ----------------------------------------------------------------------------
    #   This, too, pulled out of get_config(). Called only from birdland.py, never from build-tables.py

    def initialize_database( self, database ):

        text = []

        if SQLITE and database == 'sqlite':
            dbpath = Path( self.home_confdir, self.sqlite_database )

            text.append( f"""\nThe database file {dbpath} does not exist.
                            It will be created with the music index and YouTube index data shipped with Birdland.
                            This will take several seconds to a minute or so.\n""" )

        if MYSQL and database == 'mysql':
            db = self.mysql_database

            text.append( f"""\nThe database {db} will be build with the music index and 
                            YouTube index data shipped with Birdland.
                            This will take several seconds to a minute or so.\n""" )

        text.append( f"""When Birdland launches go to File->Settings, configure the location of your music, audio, and midi files.
                        Then select 'Database->Rebuild All Tables' to add your files to the database.""" )

        text.append( f"""\nClick OK to continue.\n""" )

        self.do_popup( '\n'.join( text ) )

        rcode = self.build_database( database )

        if rcode:
            sys.exit(1)

    # --------------------------------------------------------------------------
    #   WRW 19 Feb 2022 - Initialize the database with build_tables.py. Has database option for
    #   mysql vs. sqlite.
    #   WRW 27 Mar 2022 - Looks like I neglected to consider case where build_tables.py is a module
    #       here. Use run_external_command() instead of direct call to subprocess.Popen()

    #   WRW 18 May 2022 - There was a nasty (possible) bug in PySimpleGUI introduced between 4.57 and 4.60
    #       that caused it to hang when all three of:
    #           echo_stdout_stderr = True
    #           reroute_stdout = True
    #           reroute_stdout_to_here() is called.
    #   I reported it today and will suppress the reroute_stdout_to_here()     
    #       when run_external_command_quiet() is called from here.
    #   Also, I see no need for echo_stdout_stderr = True. Don't need the output to stdout/stderr other than
    #       for debuggin so remove it.

    def build_database( self, database ):

        build_title = \
            self.sg.Text( text='Results of Database Build',
                     font=("Helvetica", 10),
                     justification='left',
                     pad=((4,4), (8,8)),
                     # size=,
            )

        build_text = \
            self.sg.Multiline( default_text='',
                    key='build-text',
                    font=("Courier", 10 ),
                    write_only = True,
                    auto_refresh = True,
                    size=(120, 40),
                    expand_x = True,
                    expand_y = True,
                    autoscroll = True,
                #   echo_stdout_stderr = True,          # WRW 18 May 2022 - Removed.
                    reroute_stdout = True,
                    reroute_stderr = True,
                    pad = ((0,0),(0,8)),
            )

        button_close = self.sg.Button('Close', key='build-button-close', font=("Helvetica", 9), pad=((0,0),(0,8)), )
      # button_run   = self.sg.Button('Run', key='build-button-run', font=("Helvetica", 9), pad=((2,2),(2,1)), )
      # build_layout = [ [build_title], [ build_text ], [button_run, button_close] ]
        build_layout = [ [build_title], [ build_text ], [button_close] ]

        build_window = self.sg.Window( 'Birdland Build Tables',
                            return_keyboard_events=False,
                            resizable=True,
                            icon=BL_Icon,
                            finalize = True,
                            text_justification = 'left',                     
                            layout=build_layout,
                            keep_on_top = True,
                           )

        # -------------------------------
        # command = [ 'build_tables.py', '--all', '-c', self.confdir.as_posix(), '-d', database ]
        # command = [ 'ls', '-l' ]      # for testing.

        #   WRW 27 Mar 2022 - Migrate to use run_external_command(). Previously neglected to consider
        #   commands included as modules. Ouch!

        if True:
            command = [ 'build_tables.py', '--all', '-c', self.confdir.as_posix(), '-d', database ]
         #  command = [ 'bl-build-tables', '--all', '-c', self.confdir.as_posix(), '-d', database ]

            rcode = self.fb.run_external_command_quiet( command, build_window[ 'build-text' ], True )

        else:
            command = [ 'build_tables.py', '--all', '-c', self.confdir.as_posix(), '-d', database ]
            # global extcmd_popen       # /// RESUME - something fishy here.

            # if extcmd_popen:
            #     extcmd_popen.kill()
            #     extcmd_popen = None

            extcmd_popen = subprocess.Popen( command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True )
            for line in extcmd_popen.stdout:
                build_window['build-text' ].print( line, end='' )

            extcmd_popen.stdout.close()
            rcode = extcmd_popen.wait()

        if rcode:
            build_window[ 'build-text' ].print( f"\nDatabase build failed, { ' '.join( command )} returned exit code: {rcode}" )
            build_window[ 'build-text' ].print( f"Click Close exit." )

        else:
            build_window[ 'build-text' ].print( f"\nDatabase build completed successfully." )
            build_window[ 'build-text' ].print( f"Click Close to launch Birdland with default configuration file." )
            build_window[ 'build-text' ].print( f"Then File->Settings to configure location of music, audio, and midi files." )

        while True:
            event, values = build_window.Read( )
            if event == self.sg.WINDOW_CLOSED:
                break

            if event == 'build-button-close':
                build_window.close()
                break

        return rcode

    # ----------------------------------------------------------------------------
    #   25 Feb 2022 - This applies only to MySql. Already filtered before calling.
    #   Get user and password from user if not already in config file.
    #   Set temporarily internal but not in config file?

    def get_user_and_password( self, confdir ):

        text = f"""
        Please enter 'Database User' and 'Database Password' fields to access the MySql {self.sqlite_database} database.\
        You can change them later in the 'File->Settings' menu.\n
        You can also enter the locations of your media files and other parameters\
        now or also later through the 'File->Settings' menu.\n
        Please first create the {self.mysql_database} database if you have not already done so.\n
        Click 'Save' to save the parameters in your {self.config_file} file.
        """

        text = re.sub( ' +', ' ', text )
        text = re.sub( '\n ', '\n', text )          # Remove space at betinning of line

        if( not self.v.database_user or self.v.database_user == '***' and
            not self.v.database_password or self.v.database_password == '***' ):
            res = self.do_configure( first=True, text=text, confdir=confdir )
            return res

        return True

# ----------------------------------------------------------------------------

if __name__ == '__main__':

    # import PySimpleGUI as sg

    conf = Config()
    # conf.set_classes( sg )

    # conf.set_cwd( os.getcwd() )

    os.chdir( os.path.dirname(os.path.realpath(__file__)))      # Non-operational
    # conf.set_install_cwd( os.getcwd() )

    config = conf.get_config()          # Non-operational
    conf.set_class_variables()

    # folders = [ x for x in config['System']['Music_File_Folders'].split( '\n' ) if x ]
    # for folder in folders:
    #     print( folder )

    # print( config['System'][ 'index_sources'] )
    # sources = [ x for x in config['System']['index_sources'].split( '\n' ) if x ]
    
    for source in conf.get_sources():
        print( source )
        print( "  ", config['Source'][source]['folder'] )
        print( "  ", config['Source'][source]['command'] )
        print()

    # for folder in folders:
    #     print( folder )

    # --------------------------------------------------------------
    #   The new reference style is used throughout birdland.py and other modules now.

    print( "-----------------------" )
    print( "New config references" )
    print( conf.val( 'select_limit' ) )
    print( conf.val( 'music_file_root' ))
    print( conf.val( 'audio_file_root' ) )
    print( conf.val( 'external_music_viewer' ) )
    print( conf.val( 'external_audio_player' ) )
    # print( conf.val( 'source_priority' ) )

    # priorities = conf.val( 'source_priority' )
    # for priority in priorities:
    #     print( priority )

    config_file = Path( '/tmp/junk-bluebird.conf' )
    conf.save_config( config, config_file )

    print( '' )
    print( 'Example of conf.val( item )')
    for item in [ 'music_file_root', 'music_file_folders', 'canonical2file', 'music_index_dir' ]:
        print( f"Item: {item}: Value: {conf.val( item )}" )

    print( '' )
    print( 'Example of source-specific values')
    print( conf.val( 'src', 'Sher' ) )
    print( conf.val( 'folder', 'Skrivarna' ) )
    print( conf.val( 'command', 'MikelNelson' ) )

    print( conf.val( 'sheetoffsets', 'Sher' ) )
    print( conf.val( 'local2canon',  'Sher' ) )
    print( conf.val( 'localbooknames', 'Sher' ) )

    print( "c2f map:", conf.val( 'c2f_editable_map' ) )
    print( "c2f folders:", conf.val( 'c2f_editable_music_folders' ) )

    print( "audiofile_index:", conf.val( 'audiofile_index' ) )
    print( "audiofile_index_file:", conf.audiofile_index_file )



    # --------------------------------------------------------------
