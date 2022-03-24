#!/usr/bin/python

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import shutil
import sys

# -----------------------------------------------------------------------------------------------

class L2C():

    # --------------------------------------------------------------
    def __init__( self ):
        self.srcs = None
        self.local = None
        self.source = None
        self.dirty = False
        self.local_loaded = False
        self.table_loaded = False

    # -----------------------------------

    def set_elements( self, dc, canonical_table, local_table, src_combo ):
        self.dc = dc
        self.canonical_table = canonical_table
        self.local_table = local_table
        self.src_combo = src_combo

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
        self.src_combo.update( values=self.srcs )

        self.canonicals = self.fb.get_canonicals()
        self.fb.safe_update( self.canonical_table, self.canonicals, None )

    def set_class_config( self ):
        pass

    # ---------------------------------------------------
    #   Traverse source-specific Local-Book-Names.txt file.
    #   Join with lines in Local2Canon.txt with contents of that
    #       file if match otherwise '-'
    #   Populate local_table with data.

    def load_local_table( self, src ):
        self.source = self.fb.get_source_from_src( src )

        # /// RESUME - should I add another conf accessor for source-specific items not in config file?
        #   This is OK for now.

        # local2canon_path = Path( self.conf.index_source_dir, self.source, self.conf.local2canon )
        # local_books_path = Path( self.conf.index_source_dir, self.source, self.conf.localbooknames )

        local2canon_path =  self.conf.val( 'local2canon', self.source )
        local_books_path =  self.conf.val( 'localbooknames', self.source )

        local2canon = {}

        if local2canon_path.is_file():
            with open( local2canon_path ) as local2canon_fd:
                for line in local2canon_fd:
                    line = line.strip()
                    local, canon = line.split( '|' )
                    local = local.strip()
                    canon = canon.strip()
                    local2canon[ local ] = canon
        else:
            print( f"ERROR: Can't find {local2canon_path} for {self.source}" )
            sys.exit(1)

        if local_books_path.is_file():
            with open( local_books_path ) as ifd:
                local_books = ifd.readlines()
                local_books = [ x.strip() for x in local_books ]
        else:
            print( f"ERROR: Can't find {local_books_path} for {self.source}" )
            sys.exit(1)

        self.locals = []

        for local_book in sorted( local_books ):
            local_book = local_book.strip()

            if local_book in local2canon:
                canon = local2canon[ local_book ]
            else:
                canon = '-'

            self.locals.append( [ local_book, canon ] )

        self.fb.safe_update( self.local_table, self.locals, None )

    # ---------------------------------------------------

    def process_events( self, event, values ):

        # ------------------------------------------
        #   Select 'Source' in dropdown menu. Populate the locals table.
        #   Canonicals table already populated above.

        if event == 'local2canonical-mgmt-src-combo':
            src = values[ 'local2canonical-mgmt-src-combo' ]
            self.load_local_table( src )
            self.dirty = False
            self.local_loaded = True

            return True

        # ------------------------------------------
        #   Click on 'Link' button.

        elif event == 'local2canonical-mgmt-link':
            found = 0

            if 'local2canonical-canonical-mgmt-table' in values and len( values[ 'local2canonical-canonical-mgmt-table' ] ):
                index = values[ 'local2canonical-canonical-mgmt-table' ][0]
                selected_canonical = self.canonicals[ index ][0]
                found += 1

            if 'local2canonical-local-mgmt-table' in values and len( values[ 'local2canonical-local-mgmt-table' ] ):
                index = values[ 'local2canonical-local-mgmt-table' ][0]
                selected_local_row = index
                found += 1

            if found == 2:
                self.locals[ selected_local_row ][ 1 ] = selected_canonical
                new_selected_local_row = selected_local_row + 1 if selected_local_row + 1 < len( self.locals ) else len( self.locals ) -1
                self.fb.safe_update( self.local_table, self.locals, [new_selected_local_row] )
                self.dirty = True

            else:
                t = """\nPlease select a row in the 'All Canonical Names' table and a
row in the 'Local Name / Linked Canonical Name' table.\n"""
                self.conf.do_popup( t )

            return True

        # ------------------------------------------
        elif event == 'local2canonical-mgmt-clear-one':
            if 'local2canonical-local-mgmt-table' in values and len( values[ 'local2canonical-local-mgmt-table' ] ):
                index = values[ 'local2canonical-local-mgmt-table' ][0]
                selected_local_row = index
                self.locals[ selected_local_row ][ 1 ] = ''
                self.fb.safe_update( self.local_table, self.locals, None )
                self.dirty = True

            else:
                t = """\nPlease select a row in the 'Local Name / Linked Canonical Name' table.\n"""
                self.conf.do_popup( t )

            return True

        # ------------------------------------------
        #   Click on 'Save' button. Backup file and
        #       write updated on if any changes.

        elif event == 'local2canonical-mgmt-save':
            if not self.local_loaded:
                t = """\nYou have not selected a source, nothing to save.\n"""
                self.conf.do_popup( t )
                return True

            if not self.dirty:
                t = """\nYou have not made any changes, nothing to save.\n"""
                self.conf.do_popup( t )
                return True

            # local2canon_path = Path( self.source, self.conf.local2canon )

            local2canon_path =  self.conf.val( 'local2canon', self.source )
            backup_file = Path( local2canon_path.parent, local2canon_path.name + '.bak' )

            if Path(local2canon_path).is_file():           # Possibly nothing to backup
                shutil.copyfile( local2canon_path.as_posix(), backup_file.as_posix() )

            with open( local2canon_path, "w" ) as ofd:

                for row in self.locals:
                    local = row[0]
                    canonical = row[1]

                    # Only save lines without '-'. They are added above for local book names without canonical to local data.

                    if canonical != '-':        
                        print( f'{local} | {canonical}', file=ofd )                

                self.conf.do_popup( f"\nSaved to: {local2canon_path}\nSaved backup to {backup_file}\n" )
            return True

        # ------------------------------------------
        #   No events recognized, tell calling program to continue processing events.

        return False

# -----------------------------------------------------------------------------------------------
