# -----------------------------------------------------------------------
#   fb_search.py - Search functions, pulled out of birdland.py
#       WRW 30 Mar 2022

#   /// RESUME OK - I did this in a hurry to reduce the size of birdland.py
#       and confine all search-related code to one place. Perhaps
#       change this to a class so don't have any/as many globals here.
#       Think a bit more about it. OK for now.

# -----------------------------------------------------------------------

from collections import defaultdict

# -----------------------------------------------------------------------

def set_driver( t1, t2, t3 ):
    global MYSQL, SQLITE, FULLTEXT
    MYSQL = t1
    SQLITE = t2
    FULLTEXT = t3

# -----------------------------------------------------------------------

def set_classes( aconf, afb ):
    global conf, fb                
    conf = aconf
    fb = afb

# -----------------------------------------------------------------------

def set_elements( tdc, tSelect_Limit, twindow, tstatus_bar ):
    global dc
    dc = tdc

    global Select_Limit
    Select_Limit = tSelect_Limit

    global window
    window = twindow

    global status_bar
    status_bar = tstatus_bar

# -----------------------------------------------------------------------
#   Add a plus sign in front of each word in val.

def make_boolean( val ):
    parts = val.split()
    t = [ '+' + x for x in parts ]
    val = " ".join( t )
    return val

# --------------------------------------------------------------------------
#   Replace %s with ? if using SQLITE

def fix_query( query ):
    if SQLITE:
        query = query.replace( '%s', '?' )
    return query

# ---------------------------------------------------------------------------

def nested_dict(n, type):           # Small enough to just duplicate in a couple of sources.
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))

# ---------------------------------------------------------------------------
#   Select one of each canonical by src priority
#   This, and the following, are now clean and simple. Not always so. It took quite
#   a while and a lot of frustration to figure out what I really wanted to do here.

def select_unique_canonicals( data ):
    results = []
    titles = nested_dict( 2, list )     # This is pretty cool.

    for row in data:            # Build dict by title and canonical containing incoming data
        titles[ row['title'] ][ row['canonical'] ].append( row )

    for title in titles:                                
        for canonical in titles[ title ]:
            row = sorted( titles[ title ][canonical], key = lambda x: int( x['src_priority']), reverse=False )[0]
            results.append( row )

    return results

# -----------------------------------------------------------------------
#   Select one of each src by canonical priority

def select_unique_srcs( data ):
    results = []
    titles = nested_dict( 2, list )     # So is this.

    for row in data:                    # Build a dict indexed by title and src
        titles[ row[ 'title' ] ][ row['src'] ].append( row )

    for title in titles:                                
        for src in titles[ title ]:
            row = sorted( titles[ title ][src], key = lambda x: int( x['canonical_priority']), reverse=False )[0]
            results.append( row )

    return results

# -----------------------------------------------------------------------
#   Select one of each title by canonical priority.
#   No need to deal further with srcs as they will disappear once I build the consolidated index.
#   WRW 9 Apr 2022 - Trying new approach using priority in canonical file.
#   Add priority columns to data, sort on canonical priority column, take first element, 
#        remove priority columns as last step before table update.

def select_unique_titles( data ):
    results = []
    titles = nested_dict( 1, list )     # This is pretty cool.

    for row in data:                    # Build dict by title
        title = row[ 'title' ]          # New named variables so we remember what we are doing.
        titles[ title ].append( row )

    #   Sort data for each title on canonical_priority_col and take top row.

    for title in titles:
        row = sorted( titles[ title ], key = lambda x: int( x['src_priority']), reverse=False )[0]
        results.append( row )

    return results

# -----------------------------------------------------------------------
#   WRW 10 Apr 2022 - Convert from dict to list and remove priority columns.

def strip_priority_data( data ):
    res = []
    for row in data:
        res.append( [ row['title'], 
                      row['composer'],
                      row['canonical'],
                      row['page'],
                      row['sheet'],
                      row['src'],
                      row['local'],
                      row['file'] 
                    ] )
    return res

# -----------------------------------------------------------------------

def do_query_music_file_index_with_join( dc, title, composer, lyricist, album, artist, src, canonical ):

    # window.set_cursor( "clock" )      # looks terrible. With my own FULLTEXT don't need any 'busy' indicator.
    # window.refresh()

    table = []
    data = []
    wheres = []
    count = 0

    # query = "SET PROFILING = 1"
    # dc.execute( query )

    if title:
        if MYSQL:
            wheres.append( "MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""titles_distinct_fts.title MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "titles_distinct.title", title )
                wheres.append( w )
                data.extend( d )

    if composer:
        if MYSQL:
            wheres.append( "MATCH( composer ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( composer )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""composer MATCH ?""" )
                data.append( composer )
            else:
                w, d = fb.get_fulltext( "composer", composer )
                wheres.append( w )
                data.extend( d )

    if lyricist:
        if MYSQL:
            wheres.append( "MATCH( lyricist ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( lyricist )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""lyricist MATCH ?""" )
                data.append( lyricist )
            else:
                w, d = fb.get_fulltext( "lyricist", lyricist )
                wheres.append( w )
                data.extend( d )

    if src:
        if MYSQL:
            wheres.append( "titles.src = %s" )
            data.append( src )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""titles.src MATCH ?""" )
                data.append( src )
            else:
                w, d = fb.get_fulltext( "titles.src", src )
                wheres.append( w )
                data.extend( d )

    if canonical:
        if MYSQL:
            wheres.append( "MATCH( local2canonical.canonical ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( canonical )
        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""local2canonical.canonical MATCH ?""" )
                data.append( canonical )
            else:
                w, d = fb.get_fulltext( "local2canonical.canonical", canonical )
                wheres.append( w )
                data.extend( d )

    if album:
        if MYSQL:
            wheres.append( """titles_distinct.title IN
                                   ( SELECT title FROM audio_files
                                     WHERE MATCH( album ) AGAINST( %s IN BOOLEAN MODE ) )
                           """ )
            data.append( album )

        if SQLITE:
            if FULLTEXT:
                wheres.append( """titles_distinct.title IN
                    ( SELECT title FROM audio_files
                      WHERE album MATCH ? ) """ )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "album", album )
                wheres.append( f"""titles_distinct.title IN
                                   ( SELECT title FROM audio_files WHERE {w} )
                                """ )
                data.extend( d )

    if artist:
        if MYSQL:
            wheres.append( """titles_distinct.title IN
                               ( SELECT title FROM audio_files
                                 WHERE MATCH( artist ) AGAINST( %s IN BOOLEAN MODE ) )
                           """ )
            data.append( artist )

        if SQLITE:
            if FULLTEXT:
                wheres.append( """titles_distinct.title IN
                    ( SELECT title FROM audio_files
                      WHERE artist MATCH ? ) """ )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "artist", artist )
                wheres.append( f"""titles_distinct.title IN
                                   ( SELECT title FROM audio_files WHERE {w} )
                                """ )
                data.extend( d )


    # -----------------------------------------------------------------------
    #   WRW 24 Feb 2022 - I think I screwed up 'include_titles_missing_file' settings considering
    #       it for local2canonical instead of canonical2file.

    if len( data ):
        where_clauses = "WHERE " + " AND ".join( wheres )

        # local2canonical_join = 'JOIN local2canonical USING( local, src )'
        local2canonical_join = 'JOIN local2canonical ON (local2canonical.local = titles.local AND local2canonical.src = titles.src)'

        if conf.val( 'include_titles_missing_file' ):
            # canonical2file_join = 'LEFT JOIN canonical2file USING( canonical )'
            canonical2file_join = 'LEFT JOIN canonical2file ON canonical2file.canonical = canonicals.canonical'
        else:
            # canonical2file_join = 'JOIN canonical2file USING( canonical )'
            canonical2file_join = 'JOIN canonical2file ON canonical2file.canonical = canonicals.canonical'

        # ---------------------------------------------------------------------------
        if MYSQL:
            query = f"""
                SELECT titles_distinct.title, titles.composer, titles.sheet, titles.src, titles.local,
                local2canonical.canonical, canonical2file.file,
                src_priority.priority AS src_priority, canonicals.priority AS canonical_priority /* WRW 9 Apr 2022 - added */
                FROM titles_distinct
                JOIN titles USING( title_id )
                JOIN src_priority ON src_priority.src = titles.src                      /* WRW 9 Apr 2022 - added */
                {local2canonical_join}
                JOIN canonicals ON canonicals.canonical = local2canonical.canonical     /* WRW 9 Apr 2022 - added */
                {canonical2file_join}
                {where_clauses}
                ORDER BY titles_distinct.title, local2canonical.canonical, titles.src   
                LIMIT {Select_Limit}
            """

        # ---------------------------------------------------------------------------
        #   This was a real pain to get working. Turns out that fullword search in sqlite3 can't
        #   have an ORDER BY clause for anything but rank, at least that's what appears to be the
        #   case from some toy tests.
        #   WRW 10 Apr 2022 - Looks like sqlite3 and mysql treat JOIN a bit differently. After
        #   additions of 9 Apr 2022 mysql complained but sqlite3 did not. Had to change
        #   order of JOIN to resolve.

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT titles_distinct_fts.title,
                    titles.composer, titles.sheet, titles.src, titles.local,
                    local2canonical.canonical, canonical2file.file,
                    src_priority.priority AS src_priority, canonicals.priority AS canonical_priority /* WRW 9 Apr 2022 - added */
                    FROM titles_distinct_fts
                    JOIN titles USING( title_id )
                    JOIN src_priority ON src_priority.src = titles.src                      /* WRW 9 Apr 2022 - added */
                    {local2canonical_join}
                    JOIN canonicals ON canonicals.canonical = local2canonical.canonical     /* WRW 9 Apr 2022 - added */
                    {canonical2file_join}
                    {where_clauses}
                    ORDER BY rank
                    LIMIT {Select_Limit}
                """

            else:
                query = f"""
                    SELECT titles_distinct.title,
                    titles.composer, titles.sheet, titles.src, titles.local,
                    local2canonical.canonical, canonical2file.file,
                    src_priority.priority AS src_priority, canonicals.priority AS canonical_priority    /* WRW 9 Apr 2022 - added */
                    FROM titles_distinct
                    JOIN titles USING( title_id )
                    JOIN src_priority ON src_priority.src = titles.src                      /* WRW 9 Apr 2022 - added */
                    {local2canonical_join}
                    JOIN canonicals ON canonicals.canonical = local2canonical.canonical     /* WRW 9 Apr 2022 - added */
                    {canonical2file_join}
                    {where_clauses}
                    ORDER BY titles_distinct.title, local2canonical.canonical, titles.src   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )      # Replace %s with ? for SQLITE

        if False:
            print( "Query", query )
            print( "Data", data )

        # ---------------------------------------------------------------------
        #   WRW 10 Apr 2022 - switch from list to dict.

        dc.execute( query, data )
        rows = dc.fetchall()

        # headings = [ "Title", "Composer", "Canonical Book Name", "Page", "Sheet", "Source", "Local Book Name", "File" ],

        if rows:
            for row in rows:
                # title = row[ 'title' ]
                # composer = row[ 'composer' ]
                # canonical = row[ 'canonical' ]
                # sheet = row[ 'sheet' ]
                # src = row[ 'src' ]
                # file = row[ 'file' ]
                # local = row[ 'local' ]
                # src_priority = row[ 'src_priority' ]             # WRW 9 Apr 2022 - added
                # canonical_priority = row[ 'canonical_priority' ]                              # WRW 9 Apr 2022 - added

                # page = fb.get_page_from_sheet( sheet, src, local )
                page = fb.get_page_from_sheet( row[ 'sheet' ], row[ 'src' ], row[ 'local' ] )

                # table.append( [ src_priority, canonical_priority, title, composer, canonical, page, sheet, src, local, file ] )

                table.append( { 'src_priority' : row[ 'src_priority' ],
                                'canonical_priority' : row[ 'canonical_priority' ],
                                'title' : row[ 'title' ],
                                'composer' : row[ 'composer' ],
                                'canonical' : row[ 'canonical' ],
                                'page' : page,
                                'sheet' : row[ 'sheet' ],
                                'src' : row[ 'src' ],
                                'local' : row[ 'local' ],
                                'file' : row[ 'file' ]
                               } )

        if MYSQL:
            query = f"""
                SELECT count(*) cnt
                FROM titles_distinct
                JOIN titles USING( title_id )
                {local2canonical_join}
                {where_clauses}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT count(*) cnt
                    FROM titles_distinct_fts
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {where_clauses}
                """
            else:
                query = f"""
                    SELECT count(*) cnt
                    FROM titles_distinct
                    JOIN titles USING( title_id )
                    {local2canonical_join}
                    {where_clauses}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return (table, count)

# --------------------------------------------------------------------------

def do_query_music_file_index( dc, title, composer, lyricist, src, canonical ):
    return do_query_music_file_index_with_join( dc, title, composer, lyricist, None, None, src, canonical )

# --------------------------------------------------------------------------
#   WRW 19 Feb 2022 - Toyed around with searching filename in audio_files
#       but don't think it is a good idea. Nothing in filename not already
#       in the metadata

#   wheres.append( "MATCH( file ) AGAINST( %s IN BOOLEAN MODE )" )
#   data.append( title )

#   wheres.append( f"""file MATCH ?""" )
#   data.append( title )

#   w, d = fb.get_fulltext( "file", title )
#   wheres.append( w )
#   data.extend( d )

def do_query_audio_files_index( dc, title, album, artist ):
    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""title MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "title", title )
                wheres.append( w )
                data.extend( d )

    if album:
        if MYSQL:
            wheres.append( "MATCH( album ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( album )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""album MATCH ?""" )
                data.append( album )
            else:
                w, d = fb.get_fulltext( "album", album )
                wheres.append( w )
                data.extend( d )

    if artist:
        if MYSQL:
            wheres.append( "MATCH( artist ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( artist)

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""artist MATCH ?""" )
                data.append( artist )
            else:
                w, d = fb.get_fulltext( "artist", artist )
                wheres.append( w )
                data.extend( d )

    # ---------------------------------------------------

    if len( data ):
        where = "WHERE " + " AND ".join( wheres )

        if MYSQL:
            query = f"""
                SELECT title, artist, album, file
                FROM audio_files
                {where}
                ORDER BY title, artist   
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title, artist, album, file
                    FROM audio_files_fts
                    {where}
                    ORDER BY title, artist   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT title, artist, album, file
                    FROM audio_files
                    {where}
                    ORDER BY title, artist   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                title = row[ 'title' ]
                artist = row[ 'artist' ]
                album = row[ 'album' ]
                file = row[ 'file' ]
                table.append( [ title, artist, album, file ] )

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM audio_files
                {where}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM audio_files_fts
                    {where}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM audio_files    
                    {where}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_music_filename( dc, title ):

    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( rpath ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

            wheres.append( "MATCH( file ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( f"""rpath MATCH ?""" )
                data.append( title )

                wheres.append( f"""file MATCH ?""" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "rpath", title )
                wheres.append( w )
                data.extend( d )

                w, d = fb.get_fulltext( "file", title )
                wheres.append( w )
                data.extend( d )

    if len( data ):

        where = "WHERE " + " OR ".join( wheres )

        if MYSQL:
            query = f"""
                SELECT rpath, file
                FROM music_files
                {where}
                ORDER BY rpath, file
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT rpath, file
                    FROM music_files_fts
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT rpath, file
                    FROM music_files
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                rpath = row[ 'rpath' ]
                file = row[ 'file' ]
                table.append( [ rpath, file ] )

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM music_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM music_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM music_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_midi_filename( dc, title ):

    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( rpath ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

            wheres.append( "MATCH( file ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( "rpath MATCH ?" )
                data.append( title )

                wheres.append( "file MATCH ?" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "rpath", title )
                wheres.append( w )
                data.extend( d )

                w, d = fb.get_fulltext( "file", title )                                          
                wheres.append( w )
                data.extend( d )

    if len( data ):
        where = "WHERE " + " OR ".join( wheres )
        if MYSQL:
            query = f"""
                SELECT rpath, file
                FROM midi_files    
                {where}
                ORDER BY rpath, file   
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT rpath, file
                    FROM midi_files_fts
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT rpath, file
                    FROM midi_files
                    {where}
                    ORDER BY rpath, file   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            table = [ [ row[ 'rpath' ], row[ 'file' ] ] for row in rows ]

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM midi_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM midi_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM midi_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_chordpro( dc, title, artist ):
    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( "title MATCH ?" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "title", title )
                wheres.append( w )
                data.extend( d )

    if artist:
        if MYSQL:
            wheres.append( "MATCH( artist ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( artist )

        if SQLITE:
            if FULLTEXT:
                wheres.append( "artist MATCH ?" )
                data.append( artist )

            else:
                w, d = fb.get_fulltext( "artist", artist )
                wheres.append( w )
                data.extend( d )

    if len( data ):
        where = "WHERE " + " AND ".join( wheres )
        if MYSQL:
            query = f"""
                SELECT title, artist, file
                FROM chordpro_files
                {where}
                ORDER BY title, artist, file
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title, artist, file
                    FROM chordpro_files_fts
                    {where}
                    ORDER BY title, artist, file
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT title, artist, file
                    FROM chordpro_files
                    {where}
                    ORDER BY title, artist, file
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            table = [ [ row[ 'title' ], row[ 'artist' ], row[ 'file' ] ] for row in rows ]

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM chordpro_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM chordpro_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM chordpro_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_jjazz_filename( dc, title ):

    table = []
    wheres = []
    data = []
    count = 0

    if title:
        if MYSQL:
            wheres.append( "MATCH( title ) AGAINST( %s IN BOOLEAN MODE )" )
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                wheres.append( "title MATCH ?" )
                data.append( title )

            else:
                w, d = fb.get_fulltext( "title", title )
                wheres.append( w )
                data.extend( d )

    if len( data ):
        where = "WHERE " + " OR ".join( wheres )
        if MYSQL:
            query = f"""
                SELECT title, file
                FROM jjazz_files
                {where}
                ORDER BY title, file
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title, file
                    FROM jjazz_files_fts
                    {where}
                    ORDER BY title, file
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT title, file
                    FROM jjazz_files
                    {where}
                    ORDER BY title, file
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            table = [ [ row[ 'title' ], row[ 'file' ] ] for row in rows ]

        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM jjazz_files
                {where}
                LIMIT {Select_Limit}
            """
        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM jjazz_files_fts
                    {where}
                    LIMIT {Select_Limit}
                """
            else:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM jjazz_files
                    {where}
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def do_query_youtube_index( dc, title ):

    table = []
    data = []
    count = 0

    if title:
        if MYSQL:
            query = f"""
                SELECT titles_distinct.title,
                title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                FROM titles_distinct
                JOIN title2youtube ON title2youtube.title_id = titles_distinct.title_id
                WHERE MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )
                ORDER BY titles_distinct.title, title2youtube.ytitle   
                LIMIT {Select_Limit}
            """
            data.append( title )

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT title,
                    title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                    FROM titles_distinct_fts
                    JOIN title2youtube USING( title_id )
                    WHERE titles_distinct_fts.title MATCH ?
                    ORDER BY titles_distinct.title, title2youtube.ytitle   
                    LIMIT {Select_Limit}
                """
                data.append( title )

            else:
                w, d = fb.get_fulltext( "titles_distinct.title", title )
                data.extend( d )

                query = f"""
                    SELECT title,
                    title2youtube.ytitle, title2youtube.duration, title2youtube.yt_id
                    FROM titles_distinct
                    JOIN title2youtube USING( title_id )
                    WHERE {w}
                    ORDER BY titles_distinct.title, title2youtube.ytitle   
                    LIMIT {Select_Limit}
                """

        query = fix_query( query )

    # --------------------------------------------------------------------

    if len( data ):
        dc.execute( query, data )
        rows = dc.fetchall()

        if rows:
            for row in rows:
                title = row[ 'title' ]
                ytitle = row[ 'ytitle' ]
                duration = row[ 'duration' ]
                yt_id = row[ 'yt_id' ]
                table.append( [ title, ytitle, duration, yt_id ] )

        # data = []
        if MYSQL:
            query = f"""
                SELECT COUNT(*) cnt
                FROM titles_distinct
                JOIN title2youtube ON title2youtube.title_id = titles_distinct.title_id
                WHERE MATCH( titles_distinct.title ) AGAINST( %s IN BOOLEAN MODE )
            """
            # data.append( title )

        if SQLITE:
            if FULLTEXT:
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM titles_distinct_fts
                    JOIN title2youtube USING( title_id )
                    WHERE titles_distinct_fts.title MATCH ?
                """
                # data.append( title )

            else:
                # w, d = fb.get_fulltext( "titles_distinct.title", title )
                query = f"""
                    SELECT COUNT(*) cnt
                    FROM titles_distinct
                    JOIN title2youtube USING( title_id )
                    WHERE {w}
                """
                # data.extend( d )

        query = fix_query( query )
        dc.execute( query, data )
        count = dc.fetchone()[ 'cnt' ]

    return table, count

# --------------------------------------------------------------------------

def process_events( event, values ):
    global indexed_music_file_table_data, audio_file_table_data, music_file_table_data, midi_file_table_data
    global youtube_file_table_data, chordpro_file_table_data, jjazz_file_table_data
    
    if( event == 'search' or                        #   Search button or 'Enter' in search text boxes.
        event == 'exclude-duplicate-none' or        #   Also events when these buttons change.
        event == 'exclude-duplicate-titles' or
        event == 'exclude-duplicate-canonicals' or
        event == 'exclude-duplicate-srcs'
      ):

        # ---------------------------------------
        #   Gather search data

        title =                         values[ "song-title" ] if 'song-title' in values else None
        album =                         values[ "song-album" ] if 'song-album' in values else None
        artist =                        values[ "song-artist" ] if 'song-artist' in values else None
        composer =                      values[ "song-composer" ] if 'song-composer' in values else None
        lyricist =                      values[ "song-lyricist" ] if 'song-lyricist' in values else None
        src =                           values[ "local-src" ] if 'local-src' in values else None
        canonical =                     values[ "canonical" ] if 'canonical' in values else None
        join_flag =                     True if values[ 'search-join-title' ] else False
      # exclude_duplicate_none =        True if values[ 'exclude-duplicate-none' ] else False
        exclude_duplicate_titles =      True if values[ 'exclude-duplicate-titles' ] else False
        exclude_duplicate_srcs =        True if values[ 'exclude-duplicate-srcs' ] else False
        exclude_duplicate_canonicals =  True if values[ 'exclude-duplicate-canonicals' ] else False

        # ---------------------------------------
        #   Make MySql boolean search values.

        if MYSQL:
            if title:
                title = make_boolean( title )
            if album:
                album = make_boolean( album )
            if artist:
                artist = make_boolean( artist )
            if composer:
                composer = make_boolean( composer )
            if lyricist:
                lyricist = make_boolean( lyricist )

        if SQLITE:      # Nothing to be done for search terms in Sqlite3, at least for simulated fullword search.
            pass

        # ---------------------------------------
        #   Initialize all tables to no data. Update tables only when matched search selection.

        indexed_music_file_table_data = music_file_table_data = audio_file_table_data = \
            midi_file_table_data = youtube_file_table_data = chordpro_file_table_data = jjazz_file_table_data = []

        # ------------------------------------------------------------------------------
        #   Search music filename, audio file index, youtube index in database.
        #       Update associated tables.

        #   Select first tab for search results found going from left to right.
        #       Leave select/focus as is if nothing found.

        #   /// RESUME OK - include additional search terms in do_query*() functions?

        # ---------------------------------------
        #   Set True when first tab selected. Don't select others after that.

        tab_selected = False

        # ---------------------------------------
        if join_flag:
            indexed_music_file_table_data, pdf_count = do_query_music_file_index_with_join( dc, title, composer, lyricist, album, artist, src, canonical )
        else:
            indexed_music_file_table_data, pdf_count = do_query_music_file_index( dc, title, composer, lyricist, src, canonical )

        # ------------------------
        #   WRW 10 Apr 2022 - Changed this around a bit, now disjoint selection via radio buttons.

        if exclude_duplicate_titles:
            indexed_music_file_table_data = select_unique_titles( indexed_music_file_table_data )

        elif exclude_duplicate_canonicals:
            indexed_music_file_table_data = select_unique_canonicals( indexed_music_file_table_data )

        elif exclude_duplicate_srcs:
            indexed_music_file_table_data = select_unique_srcs( indexed_music_file_table_data )

        # ------------------------
        indexed_music_file_table_data = strip_priority_data( indexed_music_file_table_data )

        fb.safe_update( window['indexed-music-file-table'] , indexed_music_file_table_data, None )

        if len( indexed_music_file_table_data ):
            window.Element( 'tab-indexed-music-file-table' ).select()
            window.Element( 'tab-display-pdf' ).set_focus()
            tab_selected = True

        # ---------------------------------------
        music_file_table_data, music_count = do_query_music_filename( dc, title )
        fb.safe_update( window['music-filename-table'], music_file_table_data, None )

        if len( music_file_table_data  ) and not tab_selected:
            window.Element( 'tab-music-filename-table' ).select()
            window.Element( 'tab-music-filename-table' ).set_focus()
            tab_selected = True

        # -----------------------
        audio_file_table_data, audio_count = do_query_audio_files_index( dc, title, album, artist )
        fb.safe_update( window['audio-file-table'], audio_file_table_data, None )

        if len( audio_file_table_data  ) and not tab_selected:
            window.Element( 'tab-audio-file-table' ).select()
            window.Element( 'tab-audio-file-table' ).set_focus()
            tab_selected = True

        # -----------------------
        #   WRW 8 Feb 2022 - Add support for midi files
        midi_file_table_data, midi_count = do_query_midi_filename( dc, title )
        fb.safe_update( window['midi-file-table'], midi_file_table_data, None )

        if len( midi_file_table_data  ) and not tab_selected:
            window.Element( 'tab-midi-file-table' ).select()
            window.Element( 'tab-midi-file-table' ).set_focus()
            tab_selected = True

        # -----------------------
        #   WRW 27 Apr 2022 - Add support for chordpro files

        chordpro_file_table_data, chordpro_count = do_query_chordpro( dc, title, artist )
        fb.safe_update( window['current-chordpro-table'], chordpro_file_table_data, None )

        if len( chordpro_file_table_data  ) and not tab_selected:
            window.Element( 'tab-chordpro-index-table' ).select()
            window.Element( 'tab-chordpro-index-table' ).set_focus()
            tab_selected = True

        # -----------------------
        #   WRW 27 Apr 2022 - Add support for jjazz files
        jjazz_file_table_data, jjazz_count = do_query_jjazz_filename( dc, title )
        fb.safe_update( window['current-jjazz-table'], jjazz_file_table_data, None )

        if len( jjazz_file_table_data  ) and not tab_selected:
            window.Element( 'tab-jjazzlab-index-table' ).select()
            window.Element( 'tab-jjazzlab-index-table' ).set_focus()
            tab_selected = True

        # -----------------------
        youtube_file_table_data, youtube_count = do_query_youtube_index( dc, title )
        fb.safe_update( window['youtube-file-table'], youtube_file_table_data, None )

        if len( youtube_file_table_data  ) and not tab_selected:
            window.Element( 'tab-youtube-table' ).select()
            window.Element( 'tab-youtube-table' ).set_focus()
            tab_selected = True

        # ------------------------------------------------------------
        #   Post result counts to status bar

        status_bar.set_music_index( pdf_count, len(indexed_music_file_table_data) )
        status_bar.set_audio_index( audio_count, len(audio_file_table_data) )
        status_bar.set_music_files( music_count, len(music_file_table_data) )
        status_bar.set_midi_files( midi_count, len(midi_file_table_data) )
        status_bar.set_chordpro_files( chordpro_count, len(chordpro_file_table_data) )
        status_bar.set_jjazz_files( jjazz_count, len(jjazz_file_table_data) )
        status_bar.set_youtube_index( youtube_count, len(youtube_file_table_data) )
        status_bar.show()

        return True

    # --------------------------------------------------------------------------

    else:
        return False

# --------------------------------------------------------------------------
#   WRW 30 Mar 2022 - This strikes me as a bit messy. Better way? This is
#       consequence of pulling out of birdland.py. Maybe one at a time?<ctrl>F9

def get_search_results():
    global indexed_music_file_table_data, audio_file_table_data, music_file_table_data
    global midi_file_table_data, youtube_file_table_data, chordpro_file_table_data, jjazz_file_table_data

    return (
        indexed_music_file_table_data,
        audio_file_table_data,
        music_file_table_data,
        midi_file_table_data,
        chordpro_file_table_data, 
        jjazz_file_table_data,
        youtube_file_table_data
    )

# --------------------------------------------------------------------------
