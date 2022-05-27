#!/usr/bin/python
# --------------------------------------------------------------------------
#   extract-index-from-pdf.py

#   WRW 26 Dec 2021 - Traverse the music files. Attempt to extract an index
#       from them. Started with work in build_tables.py but moved to here.

#   Remember this before running:
#       export PYTHONPATH=../../birdland

# --------------------------------------------------------------------------

import os
import sys
import math
import json
import re
import socket
import click
import fitz
import csv
from pathlib import Path

import fb_utils
import fb_config

# --------------------------------------------------------------------------

# folder_exclude = ["MusicSheets-MusicNotes-Collection", 'Theory, Improvisation, Styles' ]
# folder_include = ["MusicSheets-MusicNotes-Collection" ]

books_exclude = [ "Alterego Fakebook (chords).pdf", "Vanilla Real Book 200.pdf" ]

#   Titles ending in these are excluded. Likely are not meaningful titles.

extensions_exclude = [ ".pdf", ".JPG", ".jpg", ".tif", ".png", ".bmp", ".gif", ".GIF", ".PDF", ".TIF" ]

ofile = Path( 'Raw-Index', 'extracted.csv' )

# --------------------------------------------------------------------------
#   The usual boilerplate because of the screwball way I'm using my Python modules.

def boilerplate( confdir ):
    global fb, conf

    fb = fb_utils.FB()
    conf = fb_config.Config()
    conf.get_config( confdir )
    conf.set_class_variables()
    fb.set_classes( conf )
    fb.set_class_config()

# --------------------------------------------------------------------------

Verbose = True
Verbose = False

# --------------------------------------------------------------------------
#   Some titles are useless for an index.
#       Ones that came from image -> pdf conversion.
#       Just 'numerics', 'page: numerics', 'numerics:numerics'

ext_histo = {}

def filter_title( title ):
    _, ext = os.path.splitext( title )

    ext_histo[ ext ] = ext_histo.setdefault( ext, 0 ) + 1

    if ext in extensions_exclude:
        if Verbose:
            print( "      Reject for 'ext':", title )
        return False

    if re.search( '^\d+$', title ):
        if Verbose:
            print( "      Reject for 'digits':", title )
        return False

    if re.search( '^\d+\s*:\s*\d+$', title ):
        if Verbose:
            print( "      Reject for 'digits : digits':", title )
        return False

    if re.search( '^[Pp]age:\s*\d+$', title ):
        if Verbose:
            print( "      Reject for 'page: digits':", title )
        return False

    if re.search( '^[Pp]age\s*\d+$', title ):
        if Verbose:
            print( "      Reject for 'page digits':", title )
        return False

    if Verbose:
        print( "      Accept:", title )
    return True

# --------------------------------------------------------------------------
#   From: https://www.pythontutorial.net/python-string-methods/python-titlecase/

def titlecase(s):
    return re.sub(
        r"[A-Za-z]+('[A-Za-z]+)?",
        lambda word: word.group(0).capitalize(),
        s)

def clean_title( title ):
    title = title.strip()
    title = title.replace( '_', ' ' )
    base, ext = os.path.splitext( title )
    if ext == '.agz':
        title = base

    title = titlecase( title )
    return title

# --------------------------------------------------------------------------

def extract_index():
    print( "Extracting index from pdf files", file=sys.stderr )
    total_count = 0
    file_count = 0
    error_count = 0
    file_count_by_ext = {}
    valid_count = 0
    file_with_toc_count = 0

    with open( ofile, 'w', newline='' ) as fd_csv:
        csv_writer = csv.writer( fd_csv )

        for folder in fb.Music_File_Folders:
        # for folder in folder_include:
            path = os.path.join( fb.Music_File_Root, folder )

            for root, file in fb.listfiles( path ):

                if file in books_exclude:
                    continue

                total_count += 1
                _, ext = os.path.splitext( file )

                rpath = root.replace( f"{fb.Music_File_Root}/", '', 1)

                if ext == '.pdf' or ext == '.PDF':
                    file_count += 1
                    file_count_by_ext[ ext ] = file_count_by_ext.setdefault( ext, 0 ) + 1
                    fpath = os.path.join( root, file )

                    # print( "OPEN:", fpath, file=sys.stderr )

                    try:
                        doc = fitz.open( fpath )
                    except Exception as e:
                        error_count += 1
                        (extype, value, traceback) = sys.exc_info()
                        print( f"ERROR on fitz.open(), type: {extype}, value: {value}", file=sys.stderr )
                        print( f"  {fpath}", file=sys.stderr  )
                        print( "", file=sys.stderr )
                        continue

                    valid_count += 1
                    page_count = doc.page_count

                    try:
                        tocs = doc.get_toc( simple=False )
                    except Exception as e:
                        error_count += 1
                        (extype, value, traceback) = sys.exc_info()
                        print( f"ERROR on get_toc(), type: {extype}, value: {value}", file=sys.stderr )
                        print( f"  {fpath}", file=sys.stderr  )
                        print( "", file=sys.stderr )
                        continue

                    if Verbose:
                        labels =  doc.get_page_labels()
                        if labels:
                            print( f"FILE: '{fpath}'" )
                            for label in labels:
                                print( "   Label:", label )
                                # numbers = doc.get_page_numbers( '3' )
                                # print( "      Numbers:", numbers )
                            
                    if tocs:
                        file_with_toc_count += 1
                        if Verbose:
                            print( f"FILE: '{fpath}'" )
                            print( "   Pages:", page_count )

                        for toc in tocs:
                            if len( toc ) == 4:
                                lvl, title, page, dest = toc

                            elif len( toc ) == 3:
                                print( "ERROR: no 'dest' found in toc", file=sys.stderr )
                                print( f"  {fpath}", file=sys.stderr  )
                                lvl, title, page = toc
                                continue

                            else:
                                print( f"ERROR: unexpected toc lenght: {len(toc)}", file=sys.stderr )
                                print( f"  {fpath}", file=sys.stderr  )
                                continue

                            if Verbose:
                                print( f"   Toc: lvl: {lvl}, title: {title}, page: {page}" )
                                if dest:
                                    print( f"   Dest: {dest}" )

                            if dest[ 'kind' ] == 0:
                                continue

                            if filter_title( title ):
                                title = clean_title( title )
                                csv_writer.writerow( [rpath, file, title, page] )
                                # print( f"{rpath}, {file}, {title}, {page}" )

                        if Verbose:
                            print( "" )

                # ---------------------------------------------------------

    print( f"   total files processed: {total_count}", file=sys.stderr )
    print( f"   pdf files processed: {file_count}", file=sys.stderr )
    for ext in file_count_by_ext:
        print( f"      {ext}: {file_count_by_ext[ ext ]}", file=sys.stderr )
    print( f"   pdf files yielding errors: {error_count}", file=sys.stderr )
    print( f"   valid pdf files: {valid_count}", file=sys.stderr )
    print( f"   pdf files with toc: {file_with_toc_count}", file=sys.stderr )

    print('', file=sys.stderr )
    print( 'Skipped Title Extensions:', file=sys.stderr )
    for ext in ext_histo:
        print( f"   {ext}: {ext_histo[ext]}", file=sys.stderr )

# --------------------------------------------------------------------------

@click.command( context_settings=dict(max_content_width=120) )
@click.option( "-c", "--confdir",               help="Use alternate config directory" )

def do_main( confdir ):
    boilerplate( confdir )
    extract_index()

# --------------------------------------------------------------------------

if __name__ == '__main__':
    do_main()

# --------------------------------------------------------------------------
