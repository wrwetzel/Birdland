#!/usr/bin/python
# -----------------------------------------------------------------------------------------------
#   1 Mar 2022 - Build a table for linking canonical to file.
#       Taken from fb_local2canon_mgmt.py

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import shutil
import sys

# -----------------------------------------------------------------------------------------------

class C2F():

    # --------------------------------------------------------------
    def __init__( self ):
        self.srcs = None
        self.local = None
        self.source = None
        self.dirty = False
        self.local_loaded = False
        self.table_loaded = False
        self.find_current_row = None

    # -----------------------------------

    def set_elements( self, dc, canonical_table, link_table, find ):
        self.dc = dc
        self.canonical_table = canonical_table
        self.link_table = link_table
        self.find_text = find
        self.find_text.bind("<Return>", "_Enter")

    # -----------------------------------

    def set_classes( self, conf, fb, pdf, meta ):
        self.conf = conf
        self.fb = fb
        self.pdf = pdf
        self.meta = meta

    # -----------------------------------
    #   Populate the tables. Can't do this at init as don't have self.fb yet.
    #   WRW 3 Mar 2022 - defer calling until tab selected so don't get
    #   error popup unnecessarily.

    def load_tables( self ):
        if self.table_loaded:
            return
        self.table_loaded = True

        self.canonicals = self.fb.get_canonicals()
        self.fb.safe_update( self.canonical_table, self.canonicals, None )

        # self.files = self.fb.get_files( 'y' )
        # self.fb.safe_update( self.file_table, self.files, None )

        # -------------------------------------------------------------------
        #   conf.val( 'canonical2file' ) returned as an array because 'rows' set in data dict.
        #   WRW 3 Mar 2022 - Not an error if can't find file. On startup it may not be configured.

        self.canon2file_path = Path( self.conf.val( 'c2f_editable_map' ) )

        self.link_table_data = []

        if not self.canon2file_path.is_file():
            self.conf.do_nastygram( 'c2f_editable_map', self.canon2file_path )
            return

        with open( self.canon2file_path ) as canon2file_fd:
            for line in canon2file_fd:
                line = line.strip()
                canon, file = line.split( '|' )
                canon = canon.strip()
                file = file.strip()
                self.link_table_data.append( [ canon, file ] )

        self.link_table_data = sorted( self.link_table_data, key=lambda x: x[1] )
        self.fb.safe_update( self.link_table, self.link_table_data, None )

    def set_class_config( self ):
        pass

    # ---------------------------------------------------

    def process_events( self, event, values ):

        # ------------------------------------------
        #   Click on 'Link' button.

        if event == 'canon2file-mgmt-link':
            found = 0

            if 'canon2file-canonical-mgmt-table' in values and len( values[ 'canon2file-canonical-mgmt-table' ] ):
                index = values[ 'canon2file-canonical-mgmt-table' ][0]
                selected_canonical = self.canonicals[ index ][0]
                found += 1

            if 'canon2file-link-mgmt-table' in values and len( values[ 'canon2file-link-mgmt-table' ] ):
                index = values[ 'canon2file-link-mgmt-table' ][0]
                selected_link_row = index
                found += 1

            if found == 2:
                self.link_table_data[ selected_link_row ][ 0 ] = selected_canonical
                new_selected_link_row = selected_link_row + 1 if selected_link_row + 1 < len( self.link_table_data ) else len( self.link_table_data ) -1
                self.fb.safe_update( self.link_table, self.link_table_data, [new_selected_link_row] )
                self.dirty = True

            else:
                t = """\nPlease select a row in the 'Canonical Name' table and a
                row in the 'Canonical Name / File Name' table.\n"""
                self.conf.do_popup( t )

            return True

        # ------------------------------------------

        elif event == 'canon2file-mgmt-clear-one':
            if 'canon2file-link-mgmt-table' in values and len( values[ 'canon2file-link-mgmt-table' ] ):
                index = values[ 'canon2file-link-mgmt-table' ][0]
                selected_link_row = index
                self.link_table_data[ selected_link_row ][ 0 ] = ''
                self.fb.safe_update( self.link_table, self.link_table_data, None )
                self.dirty = True

            else:
                t = """\nPlease select a row in the 'Canonical Name / File Name' table.\n"""
                self.conf.do_popup( t )

            return True

        # ------------------------------------------
        #   Click on 'Save' button. Backup file and
        #       write updated on if any changes.

        elif event == 'canon2file-mgmt-save':

            if not self.dirty:
                t = """\nYou have not made any changes, nothing to save.\n"""
                self.conf.do_popup( t )
                return True

            backup_file = Path( self.canon2file_path.parent, self.canon2file_path.name + '.bak' )

            if Path(self.canon2file_path).is_file():           # Possibly nothing to backup
                shutil.copyfile( self.canon2file_path.as_posix(), backup_file.as_posix() )

            with open( self.canon2file_path, "w" ) as ofd:

                for row in self.link_table_data:
                    canonical = row[0]
                    file = row[1]

                    print( f'{canonical} | {file}', file=ofd )

                self.conf.do_popup( f"\nSaved to: {self.canon2file_path}\nSaved backup to {backup_file}\n" )
            return True

        # ------------------------------------------

        elif event == 'canon-find-text-b':
            val = values[ 'canon-find-text-b' ].lower()
            if not val:
                return True

            for row in range( len( self.canonicals )):
                if val in self.canonicals[ row ][0].lower():
                    self.canonical_table.update(select_rows = [ row ] )
                    self.canonical_table.Widget.see( row + 1)
                    self.find_current_row = row + 1
                    break

            return True

        elif event == 'canon-find-text-b' + '_Enter':
            val = values[ 'canon-find-text-b' ].lower()
            if not val:
                self.find_current_row = None
                return True

            else:
                for row in range( self.find_current_row, len( self.canonicals )):
                    if val in self.canonicals[ row ][0].lower():
                        self.canonical_table.update(select_rows = [ row ] )
                        self.canonical_table.Widget.see( row + 1)
                        self.find_current_row = row + 1
                        break

            return True

        # ------------------------------------------
        #   No events recognized, tell calling program to continue processing events.

        return False

# -----------------------------------------------------------------------------------------------
