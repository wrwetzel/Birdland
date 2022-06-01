#!/bin/bash
# --------------------------------------------------------------------------------------
#   WRW 30 May 2022
#       Install.sh - Install Birdland with Package_Type given on command line.
#       Called from Install-From-Tar.sh or Install-From-GitHub.sh.
#   WRW 1 June 2022
#       No, now just install with Package_Type_Installed.txt

# --------------------------------------------------------------------------------------

Package_Type=Package_Type_Installed.txt

if [[ ! -d ~/.local ]]
then
    echo "Creating ~/.local"
    mkdir ~/.local
fi

if [[ ! -d ~/.local/bin ]]
then
    echo "Creating ~/.local/bin"
    mkdir ~/.local/bin
fi

if [[ ! -d ~/.local/share ]]
then
    echo "Creating ~/.local/share"
    mkdir ~/.local/share
fi

if [[ ! -d ~/.local/share/applications ]]
then
    echo "Creating ~/.local/share/applications"
    mkdir ~/.local/share/applications
fi

if [[ ! -d ~/.local/share/birdland ]]
then
    echo "Creating ~/.local/share/birdland"
    mkdir ~/.local/share/birdland
fi

cp -r src/*                                                     ~/.local/share/birdland

ln -sf ~/.local/share/birdland/birdland/birdland.py             ~/.local/bin/birdland
ln -sf ~/.local/share/birdland/birdland/build_tables.py         ~/.local/bin/bl-build-tables
ln -sf ~/.local/share/birdland/birdland/diff_index.py           ~/.local/bin/bl-diff-index

touch ~/.local/share/birdland/birdland/$Package_Type                                                

echo "Copied Birdland data folders to: '~/.local/share/birdland'"
echo "Linked executables in '~/.local/share/birdland/birdland' to '~/.local/bin'"
echo "Be sure '~/.local/bin' is in your PATH"
echo "Birdland executable is: 'birdland'"
echo "For more information see: 'ReadMe-GitHub.md' or './ReadMe-Tar.md'"
echo "Remove Birdland with: '~/.local/share/birdland/birdland/Remove-Birdland.sh'"
echo ""
echo "Installation complete. '../Birdland' or '../Birdland-main' are not needed for running Birdland and may be removed."
