#!/bin/bash
# --------------------------------------------------------------------------------------
#   Install-From-Tar.sh - Install Birdland from tarfile distribution
#   WRW 18 March 2022

#   Run this in the directory where found.
#   Mimics a pip install in .local

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

# ln -sf ~/.local/share/birdland/birdland/build_tables.py       ~/.local/bin/bl-build-tables
# ln -sf ~/.local/share/birdland/birdland/check_offsets.py      ~/.local/bin/bl-check-offsets
# cp src/birdland/birdland-tar.desktop                          ~/.local/share/applications/birdland.desktop
# sed "s,~,$HOME,g" src/birdland/birdland-tar.desktop >         ~/.local/share/applications/birdland.desktop

mv Package_Type_Tar.txt                                          ~/.local/share/birdland/birdland
mv Start-From-Tar.sh                                             ~/.local/share/birdland/birdland

echo "Copied Birdland data folders to: '~/.local/share/birdland'"
echo "Linked executables in '~/.local/share/birdland/birdland' to '~/.local/bin'"
echo "Be sure '~/.local/bin' is in your PATH"
echo "Birdland executable is: 'birdland'"
echo "For more information see: './ReadMe-Tar.md'"
echo "Remove Birdland with: '~/.local/share/birdland/birdland/Remove-Birdland.sh'"
echo "Installation complete. You may now delete '../Birdland'."
