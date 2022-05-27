#!/bin/sh
# ----------------------------------------------------------------------------
#   WRW 18 Mar 2022 - Working on packaging with tar.

#   Go to the directory containing the executable and launch birdland.py
#   and others. This symlinked to $HOME/.share/bin
# ----------------------------------------------------------------------------

export PYTHONPATH=$HOME/.local/share/birdland/birdland
cd $HOME/.local/share/birdland/birdland
CMD=$(basename $0)
case $CMD in
    birdland)
        exec ./birdland.py $*
        ;;
    bl-build-tables)
        exec ./build_tables.py $*
        ;;

    bl-diff-index)
        exec ./diff_index.py $*
        ;;

    *)
        echo "ERROR-DEV: Command '$0' not understood"
esac


# ----------------------------------------------------------------------------
