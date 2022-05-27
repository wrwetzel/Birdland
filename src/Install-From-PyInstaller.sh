#!/bin/bash
# --------------------------------------------------------------------------------------
#   Install-From-PyInstaller.sh - Install Birdland from PyInstaller bundled distribution.
#   WRW 18 March 2022

#   Run this in the Birdland directory where found.
#   /// RESUME Incomplete

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

# cp -r src/*                                                     ~/.local/share/birdland
# ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/birdland
# ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/bl-build-tables
# ln -sf ~/.local/share/birdland/birdland/Start-From-Tar.sh       ~/.local/bin/bl-check-offsets

# ln -sf ~/.local/share/birdland/birdland/build_tables.py       ~/.local/bin/bl-build-tables
# ln -sf ~/.local/share/birdland/birdland/check_offsets.py      ~/.local/bin/bl-check-offsets
# cp src/birdland/birdland-tar.desktop                            ~/.local/share/applications/birdland.desktop
# sed "s,~,$HOME,g" src/birdland/birdland-tar.desktop >           ~/.local/share/applications/birdland.desktop
echo "Installation complete"
