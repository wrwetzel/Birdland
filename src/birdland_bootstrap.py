#!/usr/bin/python
# ------------------------------------------------------------------------------
#   birdland_bootstrap.py - A program to startup Start-From_PYInstaller.py
#       in the src directory, which will invoke the birdland.py program.
#   This is used with the PyInstaller installation package.

#   WRW 19 Mar 2022 - Don't use __main__.py. Leave that for command line
#       invocations only.
#   WRW 20 Mar 2022 - Got rid of intermediate startup.py (or subsequently-named file).

#   Set python environment (search path and cwd) before starting birdland.
# ------------------------------------------------------------------------------

import sys
import os
from pathlib import Path
from src.birdland import main

path = Path( Path( __file__ ).parent, 'src' ).as_posix()
sys.path.append( path )
os.chdir( path )

if __name__ == '__main__':
    sys.exit( main() )
