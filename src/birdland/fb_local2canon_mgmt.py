#!/usr/bin/python

# -----------------------------------------------------------------------------------------------

from pathlib import Path
import shutil
import sys
import fb_utils
import Levenshtein

# -----------------------------------------------------------------------------------------------

class L2C():

    # --------------------------------------------------------------
    def __init__( self ):
        self.srcs = None
        self.src = None
        self.local = None
        self.source = None
        self.dirty = False
        self.local_loaded = False
        self.table_loaded = False

    # -----------------------------------

    def set_elements( self, dc, canonical_table, local_table, src_combo, find ):
        self.dc = dc
        self.canonical_table = canonical_table
        self.local_table = local_table
        self.src_combo = src_combo
        self.find_text = find
        self.find_text.bind("<Return>", "_Enter")

    # -----------------------------------

    def set_classes( self, conf, fb, pdf, meta ):
        self.conf = conf
        self.fb = fb
        self.pdf = pdf
        self.meta = meta

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
            self.src = values[ 'local2canonical-mgmt-src-combo' ]
            self.load_local_table( self.src )
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
        #   WRW 3 Apr 2022 - Need way to identify book by looking at first several songs.

        elif event == 'local2canonical-mgmt-profile':

            if not self.src:
                t = """\nPlease select a src from the 'Index Source' drop-down menu.\n"""
                self.conf.do_popup( t )
                return True

            if 'local2canonical-local-mgmt-table' in values and len( values[ 'local2canonical-local-mgmt-table' ] ):
                selected_local_row  = values[ 'local2canonical-local-mgmt-table' ][0]
                selected_local = self.locals[ selected_local_row ][ 0 ]
                selected_canonical = self.locals[ selected_local_row ][ 1 ]

            else:
                t = """\nPlease select a row in the 'Local Name / Linked Canonical Name' table.\n"""
                self.conf.do_popup( t )
                return True

            # ----------------------------
            limit = 25          # For sample display

            txt = """SELECT title, sheet FROM titles JOIN titles_distinct USING( title_id ) WHERE
                  src=%s AND local = %s ORDER BY sheet +0 LIMIT %s
                  """
            txt = fb_utils.fix_query( txt )

            data = [ self.src, selected_local, limit + 1]       # +1 for '_TitleFirst'
            self.dc.execute( txt, data )
            rows = self.dc.fetchall()

            prof = []       # Formatted list of sheets and titles in selected book
            titles = []     # Just List of titlles in the selected book

            for row in rows:
                if row['title'] != '_TitleFirst':
                    if row['sheet'] and row['title']:
                        prof.append( f"{row['sheet']:>4}   {row['title']}" )
                        titles.append( row['title'] )
                    else:
                        print( f"ERROR-DEV: None found in sheet: {row['sheet']} or title {row['title']}", file=sys.stderr )
                        print( f"   {self.src} / {selected_local}", file=sys.stderr )

            # ----------------------------
            txt = """SELECT COUNT(*) cnt FROM titles JOIN titles_distinct USING( title_id ) WHERE
                  src=%s AND local = %s                           
                  """
            txt = fb_utils.fix_query( txt )
            data = [ self.src, selected_local ]

            self.dc.execute( txt, data )
            row = self.dc.fetchone()
            count = row['cnt']

            # ----------------------------
            #   WRW 4 Apr 2022 - Trying to find similar books among all src/local but the current

            short_limit = 10        # for 'similiar' display

            similars = []
            ssrcs = self.fb.get_srcs()
            for ssrc in ssrcs:
                if ssrc == self.src:
                    continue

                slocals = self.fb.get_locals_from_src( ssrc )
                for slocal in slocals:
                    slocal = slocal[0]      # get_locals_from_src() returns list of lists for earlier need updating table.

                    txt = """SELECT title, sheet FROM titles JOIN titles_distinct USING( title_id ) WHERE
                          src=%s AND local = %s ORDER BY sheet +0 LIMIT %s
                          """
                    txt = fb_utils.fix_query( txt )

                    data = [ ssrc, slocal, short_limit + 1 ]          # 1 for '_TitleFirst'

                    self.dc.execute( txt, data )
                    rows = self.dc.fetchall()

                    stitles = []
                    for row in rows:
                        if row['title'] != '_TitleFirst':
                            stitles.append( row['title'] )

                    # others.append( f"{ssrc:4>}/{slocal:20}:" )
                    # others.append( '\n   '.join( stitles ) )

                    stargets = '\n'.join( stitles )
                    titles = titles[ 0:short_limit ]
                    targets = '\n'.join( titles )

                    d = Levenshtein.distance( targets, stargets )
                    if d < 20:
                        similars.append( f"   {d:3>} {ssrc}/{slocal}" )

            # ----------------------------
            res = []
            res.append( f"Titles for the first {limit} sheets ordered by sheet for index from:" )
            res.append( f"  src: '{self.src}'" )
            res.append( f"  local: '{selected_local}'" )
            if selected_canonical:
                res.append( f"  current canonical: '{selected_canonical}'" )
            res.append( f"  Sheets in book: {count}\n" )
            res.extend( prof )

            res.append( f"\nOther books similiar in the first {short_limit} titles:" )
            res.extend( similars )

            res = '\n'.join( res )
            self.conf.do_popup_raw( res, font=("Courier", 11 ) )
            return True

        # ------------------------------------------

        elif event == 'canon-find-text-a':
            val = values[ 'canon-find-text-a' ].lower()
            if not val:
                return True

            for row in range( len( self.canonicals )):
                if val in self.canonicals[ row ][0].lower():
                    self.canonical_table.update(select_rows = [ row ] )
                    self.canonical_table.Widget.see( row + 1)
                    self.find_current_row = row + 1
                    break

            return True

        elif event == 'canon-find-text-a' + '_Enter':
            val = values[ 'canon-find-text-a' ].lower()
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
