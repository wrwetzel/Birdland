# ----------------------------------------------------------------------------
#   __init__.py - Indicates that a directory is a package.
#       Executed when package containing it is imported.
#       i.e.
#           from birdland import birdland
#       allows you to define any variable at the package level.
# ----------------------------------------------------------------------------

import sys
import os
from pathlib import Path

# ------------------------------------------------------------
#   WRW 16 Mar 2022 - Another approach. No guessing. Packaging places            
#       a file, 'Package_Type.txt', describing the packaging type.

program_directory = Path( __file__ ).parent.resolve().as_posix()

# print( "/// __init__.py __file__", __file__ )
# print( "/// __init__.py program_directory", program_directory )
# print( "/// __init__.py at top, sys.path", sys.path )
# print( "/// __init__.py at top, cwd", os.getcwd() )

if Path( program_directory, 'Package_Type_GitHub.txt' ).is_file():
    Package_Type = 'GitHub'

elif Path( program_directory, 'Package_Type_Tar.txt' ).is_file():
    Package_Type = 'Tar'

elif Path( program_directory, 'Package_Type_Development.txt' ).is_file():
    Package_Type = 'Development'

# elif Path( program_directory, 'Package_Type_Setuptools.txt' ).is_file():
#     Package_Type = 'Setuptools'

# elif Path( program_directory, 'Package_Type_PyInstaller.txt' ).is_file():
#     Package_Type = 'PyInstaller'

# elif Path( program_directory, 'Package_Type_Nuitka.txt' ).is_file():
#     Package_Type = 'Nuitka'

else:
    print( f"ERROR-DEV: 'Package_Type_*.txt' file not found at '__init__.py' in {program_directory}", file=sys.stderr )
    sys.exit(1)     # Doesn't do anything

# print( f"/// __init__.py: Package_Type: {Package_Type}" )

# ------------------------------------------------------------

if Package_Type == 'Setuptools':

    sys.path.append( program_directory )
    os.chdir( program_directory )

    # print()
    # print( "/// __init__.py before import, sys.path", sys.path )
    # print( "/// __init__.py before import, cwd", os.getcwd() )
    # print()
    
    from birdland import birdland
    from birdland import build_tables
    from birdland import diff_index
    
    def start_birdland():
        sys.exit( birdland.main() )
    
    def start_build_tables():
        sys.exit( build_tables.main() )
    
    def start_diff_index():
        sys.exit( diff_index.main() )
