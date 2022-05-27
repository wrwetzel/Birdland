#!/bin/bash
# -------------------------------------------------------------------------------
#   convert-icons.sh

#   Convert *.svg icons in current directory, presumably Icons, to png with
#       a transparent background.
#   It assumes the color of the pixel at 1,1 is the background and converts that to transparent.
#   This is used for the PDF control icons in Birdland.

#   Must do it it two step process. Can't make transparent directly from svg it appears.

# -------------------------------------------------------------------------------

for x in *.svg
do
    ifile=$x
    ofile=${x%.svg}.png
    tmpfile=$$.png

    echo "Converting $ifile"

    convert $ifile $tmpfile
    color=$( convert $tmpfile -format "%[pixel:p{1,1}]" info:- )
    convert $tmpfile -fuzz 5% -transparent $color $ofile
done

rm $tmpfile
