#!/usr/bin/python
# --------------------------------------------------------------------------
#   build-pdf-from-image.py - Make a pdf file from image files in
#       a directory. Name pdf file from parent directory.

#       Put resultant pdf files in one folder named with indication of conversion.

#   This assumes that all image files for a single song are in one folder. The output
#       pdf is named after the folder.

# --------------------------------------------------------------------------

import os
import sys
import glob
import subprocess
import click
from pathlib import Path

import fb_config
import fb_utils

# ==========================================================================

Image_File_Extensions = [ '.jpg', '.tif', '.gif', '.bmp', '.JPG' ]

# ==========================================================================
#   os.walk( folder ) returns generator that returns list of folders and list of files
#       in 'folder'.

def listfolders( folder ):
    for root, folders, files in os.walk( folder ):
        for folder in folders:
            yield (root, folder)

# -----------------------------------------------------------------------

@click.command( context_settings=dict(max_content_width=120) )
@click.option( "-c", "--confdir",               help="Use alternate config directory" )

def convert_music_files( confdir ):
    fb = fb_utils.FB()
    conf = fb_config.Config()
    os.chdir( os.path.dirname(os.path.realpath(__file__)))      # Run in directory where this lives.

    conf.get_config( confdir )
    conf.set_class_variables()                                                       
    fb.set_classes( conf )
    fb.set_class_config()

    file_count = 0
    ofile_count = 0
    file_count_by_ext = {}

    for folder in conf.val( 'music_file_folders' ):
        if folder == conf.val( 'music_from_image' ):        # Don't even look at destination folder. Only contins .pdf anyway.
            print( "Skipping", folder )
            continue

        path = Path( conf.val( 'music_file_root' ), folder )

        print( "Processing:", path )

        for root, folder in listfolders( path ):
            fpath = Path( root, folder )
            os.chdir( fpath )
            files = glob.glob( '*' )

            image_files = []
            # base_histo = {}

            # print( fpath )
            found = False
            for file in files:
                # print( "   ", file )

                base = Path( file ).name
                ext =  Path( file ).suffix.lower()

                if ext in Image_File_Extensions:
                    image_files.append( file )
                    found = True

                    # base_histo[ base ] = base_histo.setdefault( base, 0 ) +1

                    file_count += 1
                    file_count_by_ext[ ext ] = file_count_by_ext.setdefault( ext, 0 ) + 1

            if found:
                image_files = sorted( image_files )
                # print( root, folder )
                # print( f"    fpath: {fpath}\n    folder: {folder}\n    image_files: {image_files}" )

                # print( "Base_Histo:", base_histo )

                ofile = Path( conf.val( 'music_file_root' ), conf.val( 'music_from_image' ), f"{folder}-cnv.pdf" )
                cmd = [ "convert", *image_files, ofile.as_posix() ]
                # print( cmd )

                subprocess.run( cmd )
                ofile_count += 1

    print( f"   Input files: {file_count}" )
    for ext in file_count_by_ext:
        print( f"      {ext}: {file_count_by_ext[ ext ]}" )
    print( f"   Output files: {ofile_count}" )

# --------------------------------------------------------------------------

if __name__ == '__main__':
    convert_music_files()

# --------------------------------------------------------------------------
#   WRW 24 March 2022 - On Paganini

#  Fakebook files: 1277
#      .jpg: 631
#      .gif: 257
#      .bmp: 87
#      .tif: 302

#   real    4m17.245s
#   user    4m41.011s
#   sys 0m31.868s

#   WRW 25 March 2022 - On Gershwin after removed three trailing spaces on 'Sheet Music' in birdland.conf.

#   Input files: 1277
#      .jpg: 631
3      .gif: 257
#      .bmp: 87
#      .tif: 302
#   Output files: 219

#   real    3m36.966s
#   user    3m11.739s
#   sys 0m31.319s
