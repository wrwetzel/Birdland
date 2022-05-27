#!/bin/bash
# --------------------------------------------------------------------------
#   remove-birdland.sh
#   WRW 18 Mar 2022 - Remove birdland and related cruft from ~/.local
# --------------------------------------------------------------------------

set -x
cd ~/.local
rm -f bin/birdland
rm -rf share/birdland
rm -rf lib/python3.10/site-packages/birdland*
rm -f share/applications/birdland.desktop
rm -f bin/build-tables
rm -f bin/diff-index
set +x
echo "birdland removed from common installation locations"
