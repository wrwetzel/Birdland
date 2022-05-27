#!/usr/bin/python
# --------------------------------------------------------------------------
#   fb_title_correction.py - Have a look at titles for certain patterns causing
#       mismatches. Formulate a strategy to correct them in the local-specific processing
#       or possibly as a post step in database.

#   This is called from fb_utils.add() when adding a title from the local-specific
#       processing do_*.py routines. It corrects the titles before they get into
#       the json files in Music_Index or the titles_distinct table in the database.

#   WRW 3 Feb 2022

# --------------------------------------------------------------------------

import os
import sys
import math
import json
import re
import click
import collections
import unidecode

import fb_utils

# --------------------------------------------------------------------------

Fixes = collections.Counter()

corrections = [
    ['0 Pato', 'O Pato'],
    ['0 Bebado E a Equilibrista', 'O Bebado E A Equilibrista' ],
    ['0 Bebado E A Equilibrista', 'O Bebado E A Equilibrista' ],
    ['No.251', 'No. 251' ],
    ['728 [Bass]', '728' ],
    ['728 [Eb]', '728' ],
    ['1919Rag1', '1919 Rag'],
    ['1919Rag2', '1919 Rag'],
    ['211Just One More Chance', 'Just One More Chance' ],
    ['219Blues', '2:19 Blues' ],
    ['500 Miles High (1)', '500 Miles High'],
    ['500 Miles High (2)', '500 Miles High'],
]

exceptions = [
    '1919 Rag',
    '111-44',
    '26-2',
    '34 skidoo',
    '9:20 Special',
    '4 A.M.',
    '500 Miles High',
    '502 Blues',
    '52 Points To Remember',
    '720 In The Books',
    '728',
    '77 Sunset Strip',
    '_TitleFirst',          # Dummy titles inserted for testing
    '_TitleLast',
]

# --------------------------------------------------------------------------
#   WRW 22 Feb 2022 - change from 3 or more to 1 or more

def titlecase( s ):
    return re.sub(r"[A-Za-z]{1,}('[A-Za-z]+)?", lambda mo: mo.group(0).capitalize(), s)

    # return re.sub(r"[A-Za-z]{3,}('[A-Za-z]+)?",
    #    lambda mo: mo.group(0).capitalize(), s)

def do_correction( log, ntitle ):

        def my_print( s ):
            item, val = s.split( ':', 1 )
            print( f"{item:>45}: {val}", file=log )

        if not log:
            log = open( os.devnull, 'w' )
                    
        # -----------------------------------------
        #   Haven't seen leading/trailing spaces but be cautious. 
        #   Probaby stripped in source-specific do_* code.
        #   However, one of the fixes left a trailing space.
        #   'Glory of love , The' -> 'The Glory of love '
        
        otitle = ntitle

        ntitle = ntitle.strip()     
        if len( ntitle ) == 0:      #   Did see one empty title
            my_print( f"Empty title after strip: '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Empty title after strip' ] += 1
            return None

        if otitle != ntitle:
            my_print( f"Strip spaces: '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Strip spaces' ] += 1

        # -----------------------------------------
        #   Found several titles needing correction.
                    
        found = False
        for item in corrections:
            if otitle == item[0]:
                ntitle = item[1]
                my_print( f"Correcting: '{otitle}' -> '{ntitle}'" )
                found = True
                break
        if found:   
            Fixes[ 'Corrections' ] += 1
            return ntitle

        # -----------------------------------------
        #   Suppress legitimate titles that would otherwise match and be changed.               

        found = False
        for exception in exceptions:
            if otitle.startswith( exception ):
                my_print( f"Exception: {otitle}" )
                ntitle = otitle
                found = True
                break
        if found:
            Fixes[ 'Exception' ] += 1
            return ntitle

        # -----------------------------------------
        #   Leading digits with optional - followed by space

        m = re.match( '^(\d+\s*-*\s*) (.*)$', otitle )
        if m:
            ntitle = f"{m[2]}"
            my_print( f"Leading digit(s) '{m[1]}':   '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Leading digits' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   A few of this pattern: '24: 23 - All This Time', process it separately from above

        otitle = ntitle
        m = re.match( '^(\d+: \d+\s+-\s+)(.*)$', otitle )

        if m:
            ntitle = f"{m[2]}"
            my_print( f"Leading digit(s) with colon '{m[1]}':   '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Leading digits with colon' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   A couple of this pattern: '1: Front'

        otitle = ntitle
        m = re.match( '^(\d+:\s+)(.*)$', otitle )

        if m:
            ntitle = f"{m[2]}"
            my_print( f"Leading digit(s) with colon '{m[1]}':   '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Leading digits with colon' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        # 11A - Intro To A Wild, Wild Party

        otitle = ntitle
        m = re.match( '^(\d+[AB]\s*-\s+)(.*)$', otitle )

        if m:
            ntitle = f"{m[2]}"
            my_print( f"Leading digit(s) with letter '{m[1]}':   '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Leading digits with letter' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing sequence number, possibly in parens
        #   WRW 2 Apr 2022 - Replace '\s+' with '\s*'? No, not a problem as is.

        otitle = ntitle

        m = re.match( '(.*)\s+(\(\d+\))$', otitle )
        if m:
            ntitle = f"{m[1]}"
            my_print( f"Trailing sequence number '{m[2]}': '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Trailing sequence number' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing [key] signature.

        otitle = ntitle

        m = re.match( '(.*)\s+(\[F]|\[Bb]|\[Eb]|\[Bass]|\[Ab])$', otitle )
        if m:
            ntitle = f"{m[1]}"
            my_print( f"Trailing [key] '{m[2]}': '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Trailing [key] signature' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing (key) signature with asterisk.
        #   WRW 13 Apr 2022 - Make asterisk optional.
        #   Note that this is ambiguous with article '(A)' instead of key '(A)'. Not many songs in A (3 sharps)
        #       so this loses, trailing article wins.

        otitle = ntitle

        m = re.match( '(.*)\s+((\(C#\)|\(E\)|\(Ab\)|\(Gb\)|\(B\)|\(Bbm\)|\(Gm\)|\(Bm\)|\(Fm\)|\(D\)|\(Em\)|\(Cm\)|\(Am\)|\(Dm\)|\(G\)|\(C\)|\(F\)|\(Bb\)|\(Db\)|\(Eb\)|\(Bass\)|\(Ab\))\*?)$', otitle )
        if m:
            ntitle = f"{m[1]}"
            my_print( f"Trailing (key) '{m[2]}': '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Trailing (key)* signature' ] += 1

        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing A, a, An, definitely in parens. Move it to front.
        #   WRW 2 Apr 2022 - was not working, moved parens to correct.
        #   Split into two tests. One with parens and optional leading space.

        otitle = ntitle

        m = re.match( '(.*?),?\s*\((A|a|An|an)\)$', otitle )
        if m:
            ntitle = f"{m[2]} {m[1]}"
            my_print( f"Trailing '({m[2]})': '{otitle}' -> '{ntitle}'"  )
            Fixes[ 'Trailing \'(A)\'' ] += 1
        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing A, a, An, an not in parens. Move it to front.
        #   WRW 2 Apr 2022 - was not working, moved parens to correct.
        #   Split into two tests. One without parens and required leading space.

        otitle = ntitle

        m = re.match( '(.*?),?\s+(A|a|An|an)$', otitle )
        if m:
            ntitle = f"{m[2]} {m[1]}"
            my_print( f"Trailing '{m[2]}': '{otitle}' -> '{ntitle}'"  )
            Fixes[ 'Trailing \'A\'' ] += 1
        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing 'The', definitely in parens, possibly with comma

        otitle = ntitle

        m = re.match( '(.*?)\s?,?\s+(\([Tt]he\))$', otitle )
        if m:
            ntitle = f"The {m[1]}"
            my_print( f"Trailing '{m[2]}': '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Trailing \'The\'' ] += 1
        else:
            ntitle = otitle

        # -----------------------------------------
        #   Trailing 'The', no parens, possibly with comma

        otitle = ntitle

        m = re.match( '(.*?)\s?,?\s+([Tt]he)$', otitle )
        if m:
            ntitle = f"The {m[1]}"
            my_print( f"Trailing '{m[2]}': '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Trailing \'The\'' ] += 1
        else:
            ntitle = otitle

        # -----------------------------------------
        #   WRW 23 Feb 2022 - Diacriticals are causing duplicates in titles_distinct.

        otitle = ntitle

        ntitle = unidecode.unidecode( otitle )
        if otitle != ntitle:
            my_print( f"Diacritical removal: '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Diacritical removal' ] += 1

        # -----------------------------------------
        #   Title case, a few all in upper case

        otitle = ntitle

        # ntitle = ntitle.title()
        ntitle = titlecase( otitle )
        if otitle != ntitle:
            my_print( f"Case correction: '{otitle}' -> '{ntitle}'" )
            Fixes[ 'Case correction' ] += 1

        # -----------------------------------------
        otitle = ntitle

        return ntitle

# --------------------------------------------------------------------------

def check_pages( dc, log ):
    count_match = count_mismatch = 0

    query = """
       SELECT title, titles.src, local, sheet, canonical, file
        FROM titles
        JOIN titles_distinct USING( title_id )
        JOIN local2canonical USING( local, src )
        JOIN canonical2file USING( canonical )
        ORDER BY title, canonical
    """

    dc.execute( query )
    data = []

    for row in dc:
        title = row['title']
        # src = row[ 'src' ]
        # local = row[ 'local' ]
        Fixes[ 'Total Title Count' ] += 1
                    
        title = do_correction( log, title )

        # if title:
        #     print( f"'{title}'" )

# --------------------------------------------------------------------------

def proc_one_book( src, data, file, **kwargs):
    log = kwargs['log']

    contents = data[ 'contents' ]
  # print( "src:", src, file=log )

    for content in contents:
        title = content[ 'title' ]
        if title:
            Fixes[ 'Total Title Count' ] += 1
            title = do_correction( log, title )
        else:
            Fixes[ 'Null Title Count' ] += 1

# --------------------------------------------------------------------------

def get_titles( src, **kwargs ):
    fb.get_music_index_data_by_src( src, proc_one_book, **kwargs )

# --------------------------------------------------------------------------
#   WRW 25 Feb 2022 - Changed to run from Music-Index, not database. Still
#       too late as most corrections already applied during building from
#       raw data. Why not ALL corrections applied, i.e., why do
#       we find any at all here? All explained, all OK.

def do_main( ):

    import fb_config
    import fb_utils

    global fb, conf

    conf = fb_config.Config()

    os.chdir( os.path.dirname(os.path.realpath(__file__)))
    # conf.set_install_cwd( os.getcwd() )

    fb = fb_utils.FB()

    conf.set_driver( True, False, False )     # Just test with MySql
    fb.set_driver( True, False, False )     # Just test with MySql

    conf.get_config( )      # Non-operational
    conf.set_class_variables()      # WRW 6 Mar 2022 - Now have to do this explicitly
    fb.set_classes( conf )
    fb.set_class_config()

    From_Index = False          # True to read json, False to read from MySql DB.
    From_DB = False             # True to read json, False to read from MySql DB.
    From_List = True            # True to test from list here.

    # ----------------------------------------------------------------
    #   Reads from ../Music-Index/*.json.gz

    if From_Index:
        with open( "Title-corrections-from-index.txt", "w" ) as log:
            fb.traverse_sources( get_titles, log=log )

            print( "Summary of corrections" )
            for fix in sorted( Fixes, key = lambda x: Fixes[x] ):
                print( f"{fix:>30}: {Fixes[fix]}" )

    # ----------------------------------------------------------------

    if From_DB:
        import MySQLdb
        conn = MySQLdb.connect( "localhost", conf.val( 'database_user' ), conf.val( 'database_password' ), conf.mysql_database )
        c = conn.cursor()
        dc = conn.cursor(MySQLdb.cursors.DictCursor)
    
        with open( "Title-corrections-from-titles_distinct.txt", "w" ) as log:
            check_pages( dc, log )
            # check_pages(dc, None )
    
            print( "Summary of corrections" )
            for fix in sorted( Fixes, key = lambda x: Fixes[x] ):
                print( f"{fix:>30}: {Fixes[fix]}" )
    
        conn.commit()
        conn.close

    # ----------------------------------------------------------------

    test_titles = [
        "Certain Smile",
        "Certain Smile(A)",
        "Certain Smile (A)",
        "Certain Smile (a)",
        "Certain Smile (A)",
        "Certain Smile (an)",

        "Certain SmileA",
        "Certain Smile A",
        "Certain Smile an",

        "Certain Smile(1)",
        "Certain Smile(12)",
        "Certain Smile (1)",
        "Certain Smile (12)",
        "Street Where You Live (On The)",
        "Beyond The Blue Horizon",
        "Little Tear(A)",
        "Little Tear (A)",
        "Little Tear,(A)",
        "Little Tear, (A)",
        "Little Tear, A",
    ]

    log = sys.stdout

    if From_List:
        for title in test_titles:
            ntitle = do_correction( log, title )
            print( f"{title} -> {ntitle}" )


# --------------------------------------------------------------------------

if __name__ == '__main__':
    do_main()

# --------------------------------------------------------------------------
