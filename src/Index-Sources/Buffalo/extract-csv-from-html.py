#!/usr/bin/python
# ----------------------------------------------------------------------------
#   WRW 7 Mar 2022 - extract-csv-from-html.py
#   Taken from do_buffalo.py - Extract a csv file from the raw html file so I
#   don't have to ship the raw file, a 28 MByte+ file, with Birdland.

#   Remember, the raw file "./Buffalo-Results-2-Mar-2022.html" is obtained by
#       a search at the site with an empty search field and saving the resulting
#       html file. That can be done into a folder outside this hierarchy

# ----------------------------------------------------------------------------

#   WRW 18 Sept 2020 - Explore Buffalo Fake Book Index
#   Each index item is 36 lines

#   WRW 19 Sept 2020 - Can't assume line number of items, some variation.

#   Many items for Tchaikovsky extend over several lines:
#       4 [<strong>Composer(s):</strong> <a href="results.html?composer=Tchaikovsky, Peter Ilich]
#       5 [Tchaikovsky, Peter Ilich">Tchaikovsky, Peter Ilich]
#       6 [Tchaikovsky, Peter Ilich</a>]
#       7 [<br>]

#       4 [<strong>Composer(s):</strong> <a href="results.html?composer=Tchaikovsky, Peter Ilich]
#       5 [Tchaikovsky, Peter Ilich">Tchaikovsky, Peter Ilich]
#       6 [Tchaikovsky, Peter Ilich</a>  /]
#       7 [<a href="results.html?composer=Barlow, H.">Barlow, H.</a><br>]

#   explore-v2.py - New approach, abandon fixed line.

# ----------------------------------------------------------------------------

import re
import os
import sys
import collections
from pathlib import Path

sys.path.append( "../../bin" )
import fb_utils
import fb_config

# ----------------------------------------------------------------------------
# 0 <h2>'57 Chevrolet</h2>
# 1
# 2
# 3
# 4 <strong>Composer(s):</strong> <a href="results.html?composer=Bowling, Roger">Bowling, Roger</a>
# 5 <br>
# 6
# 7
# 8
# 9
# 10
# 11
# 12
# 13
# 14 <strong>Fakebook:</strong> <a href="results.html?fakebook=Richard Wolfe's Legit Country Fake Book">Richard Wolfe's Legit Country Fake Book</a><br>
# 15
# 16
# 17 <strong>Page:</strong> 37<br>
# 18
# 19
# 20
# 21 Has lyrics <br>
# 22
# 23 <strong>Language:</strong>
# 24
# 25 English
# 26
# 27 <br>
# 28
# 29
# 30
# 31 <strong>Call Number:</strong> M;007;A9;Aa32
# 32
# 33 <hr>
# 34
# 35

# ----------------------------------------------------------------------------

Src = "~/Downloads/Buffalo-Results-2-Mar-2022.html"      # Saved from results for search for empty value

Buffalo_csv_file = "./buffalo-index.csv.gz"

Errors = "./Errors.txt"

period = 36         # Number of lines per item

Books = collections.Counter()
Elements = collections.Counter()
Missing = collections.Counter()
Empty = collections.Counter()

omitted_names = set()
included_names = set()
excludes = [ x.strip() for x in Path( 'Local-Exclusions.txt' ).read_text().split('\n') ]

# ----------------------------------------------------------------------------

def show_item( efd, item ):
    item = [ line.strip() for line in item ]   # Remove leading/trailing whitespace including newlines for error
    for i, line in enumerate( item ):
        print( f"{i:2d} [{line}]", file = efd )
    print( file = efd )

# ----------------------------------------------------------------------------

def parse( efd, name, item, pattern ):

    sitem = " ".join( item )                    # Combine all lines into one string for search
    m = re.search( pattern, sitem, re.DOTALL )
    err = False

    if not m:
        if name != 'lyricist':
            print( f"ERROR: no match for {name}", file=efd )
            show_item( efd, item )
        ret = f'<NO {name}>'
        ret = "-"
        Missing[ name ] += 1
        err = True

    else:
        ret = m[1]
        if not len( ret ):
            # print( f"ERROR: {name} empty:", file=efd )
            # show_item( item )
            ret = f'<EMPTY {name}>'
            ret = "--"
            Empty[ name ] += 1
            err = True

    ret = ret.replace( "\n", "" )      # Remove newlines, a few elements extend over multiple lines.
    ret = ret.strip()

    if not err:
        Elements[ name ] += 1

    return ret

# ----------------------------------------------------------------------------

def parse_composer( efd, item ):

    composer = parse( efd, 'composer', item, "<strong>Composer\(s\):</strong> <a.*?>(.*?)</a>" )

    # -----------------------------------------------------------------------------------------
    #   See if trailing '/' anywhere in item.
    #       Only composer might have a trailing '/'

    found_slash = False
    for line in [ line.strip() for line in item ]:   # Remove leading/trailing whitespace including newlines for comparision
        if len( line ) and line[-1] == '/':
            found_slash = True
            break

    if found_slash:
        extra_composer = parse( efd, 'extra_composer', item, "<strong>Composer\(s\):</strong> <a.*?>.*?</a>.*?<a.*?>(.*?)</a>" )
        composer = f'{composer} / {extra_composer}'

    composer = composer.replace( "\n", "" )      # Remove newlines, a few elements extend over multiple lines.
    return composer

# ----------------------------------------------------------------------------
#   Process one entry in the html file, i.e. one title.

def proc_item( fb, efd, item ):
    title = parse( efd, 'title', item, "<h2>(.*?)</h2>" )
    composer = parse_composer( efd, item )
    lyricist = parse( efd, 'lyricist', item, "<strong>Lyricist:</strong>\s*(.*?)\n" )
    book = parse( efd, 'book', item, "<strong>Fakebook:</strong> <a.*?>(.*?)</a><br>" )
    sheet = parse( efd, 'page', item, "<strong>Page:</strong>\s*(.*?)<br>" )

    Books[ book ] += 1

    # ------------------------------------------------------------------------
    #   WRW 7 Mar 2022 - Deal with excludes in later step.
    # if book not in excludes:
    if True:
        #   Print results for examination / testing
        #       print( f'{title}\n  {composer}\n  {lyricist}\n  {book}\n  {page}' )

        item = { 'title' : title,
                 'composer': composer,
                 'lyricist': lyricist,
                 'sheet': sheet,
               }

        if lyricist != '-' and lyricist != '--':
            item[ 'lyricist' ] = lyricist

        fb.add( book, item )
        included_names.add( book )

    else:
        excluded_names.add( book )

# ----------------------------------------------------------------------------
#   Print summary

def do_summary():
    with open( "Summary.txt", "w" ) as sum_fd:

        print( "Books:", file=sum_fd )
        for book in sorted( Books, key = lambda i: Books[i], reverse=True ):
            print( f'{Books[ book ]:4d}', book, file=sum_fd  )

        print( file=sum_fd  )
        print( "Elements:", file=sum_fd )
        for element in sorted( Elements, key = lambda i: Elements[i], reverse=True ):
            print( f'{Elements[ element ]:4d}', element, file=sum_fd  )

        print( file=sum_fd  )
        print( "Missing elements:", file=sum_fd   )
        for element in sorted( Missing, key = lambda i: Missing[i], reverse=True ):
            print( f'{Missing[ element ]:4d}', element, file=sum_fd   )

        print(file=sum_fd  )
        print( "Empty elements:", file=sum_fd   )
        for element in sorted( Empty, key = lambda i: Empty[i], reverse=True ):
            print( f'{Empty[ element ]:4d}', element, file=sum_fd   )

# ----------------------------------------------------------------------------

conf = fb_config.Config()
conf.get_config()
conf.set_class_variables()

fb = fb_utils.FB()
fb.set_classes( conf )
fb.set_class_config()

ipath = Path( Src ).expanduser()
with open( ipath ) as ifd, open( Errors, "w" ) as efd:
    prior_line = "<No Prior>"
    lines = ifd.readlines()
    i = 0
    in_contents = False                         # A little state machine
    while i < len( lines ):
        line = lines[i]
        line = line.strip()

        if line == '<div id="content">':        #   Start at <div id="content">
            in_contents = True

        if in_contents and line == '</div>':
            in_contents = False

        if in_contents:
            if "<h2>" in line:
                item = lines[i:i+period]

                proc_item( fb, efd, item )      # *** Bang!
                i += period
            else:
                print( f"WARNING: Line {i+1}, unexpected line: [{line}]", file=efd )
                print( f"   Prior line: [{prior_line}]", file=efd )
                i += 1
        else:
            i += 1

        prior_line = line

# ------------------------------------------------------------------------

do_summary()
fb.save_csv( "Buffalo", "Buf", Buffalo_csv_file )

t = '\n   '.join( sorted( included_names ))
print( f"Included books: \n   {t}", file=sys.stderr, flush=True )

t = '\n   '.join( omitted_names )                                                                                          
print( f"Omitted books: \n   {t}", file=sys.stderr, flush=True )

# ----------------------------------------------------------------------------
