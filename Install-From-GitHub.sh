#!/bin/bash
# --------------------------------------------------------------------------------------
#   Install-From-GitHub.sh - Install Birdland from GitHub zip or clone.
#   WRW 27 May 2022

#   Run this in the directory where found.
#   Mimics a pip install in .local
#   Taken from Install-From-Tar.sh, of which it is nearly identical.
#   Start-From-Tar.sh is same for this and not changed.

# --------------------------------------------------------------------------------------

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
ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/birdland
ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/bl-build-tables
ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/bl-diff-index

ln -sf ~/.local/share/birdland/birdland/build_tables.py         ~/.local/bin/bl-build-tables
ln -sf ~/.local/share/birdland/birdland/diff_index.py           ~/.local/bin/bl-diff-index
# cp src/birdland/birdland-tar.desktop                          ~/.local/share/applications/birdland.desktop
# sed "s,~,$HOME,g" src/birdland/birdland-tar.desktop >         ~/.local/share/applications/birdland.desktop

cp Package_Type_GitHub.txt                                       ~/.local/share/birdland/birdland
# cp Start-From-GitHub.sh                                          ~/.local/share/birdland/birdland

echo "Copied Birdland data folders to: '~/.local/share/birdland'"
echo "Linked executables in '~/.local/share/birdland/birdland' to '~/.local/bin'"
echo "Be sure '~/.local/bin' is in your PATH"
echo "Birdland executable is: 'birdland'"
echo "For more information see: './ReadMe-GitHub.md'"
echo "Remove Birdland with: '~/.local/share/birdland/birdland/Remove-Birdland.sh'"
echo "Installation complete. '../Birdland' or '../Birdland-main' are not needed for running Birdland and may be removed."
