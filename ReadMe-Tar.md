# Install Birdland from Tarfile Distribution

This information supplements the primary Birdland documentation for
installation only from the tar file package. Be sure to also see the primary
documentation as it contains much not covered here.

## System Requirements
```
    python3

    Python modules:
        click
        configobj
        Levenshtein
        mutagen
        mysqlclient             (only if using MySql database)
        pandas
        pillow                  (only if using Create Index feature)
        PyMuPDF
        PySimpleGUI
        pytesseract             (only if using Create Index feature)
        tk                      (check, may already be installed with Python)
        unidecode
        youtubesearchpython     (only to run get-youtube-links.py)
```

## Install Required Modules

Install them under your home directory. Does not require root access.
```
pip install click configobj Levenshtein mutagen mysqlclient pandas pillow --user
pip install PyMuPDF PySimpleGUI pytesseract tk unidecode youtubesearchpython --user
```

Or install them system wide. Requires root access.
```
pip install click configobj Levenshtein mutagen mysqlclient pandas pillow 
pip install PyMuPDF PySimpleGUI pytesseract tk unidecode youtubesearchpython
```

The PySimpleGUI Python module requires both tk and tkinter.
On some Linux distributions tk and tkinter are installed automatically when you install PySimpleGUI. If that is not
the case for the distribution you are using then you will have to install in manually. For example, on Ubuntu
and Ubuntu-like systems:
```
sudo apt-get install python3-tk
```

## Install Birdland

Unpack the birdland tar file *birdland-user.tar.gz* in a temporary directory. For example, if you
have *tmp* in you home directory and have downloaded the tar file into *~/Downloads*:
```
cd ~/tmp
tar -xzvf ~/Downloads/birdland-user.tar.gz
```
This creates a new directory, *Birdland*, containing the package files. Go to that directory and
run the installation script:

```
cd Birdland
Install-From-Tar.sh
```
This copies data folders to ~/.local/share/birdland and links executables to ~/.local/bin.

You may now remove the package folder in the temporary directory.
```
rm -rf ~/tmp/Birdland
```

Be sure that ~/.local/bin is in your PATH environment variable. If your shell is bash then
check your ~./bashrc file:

```
PATH=~/.local/bin:$PATH
```

## Run Birdland
The name of the executable is *birdland*. Run it from the command line:

```
birdland
```
After you run it for the first time from the command line you can then run it
from the system menu. (Birdland creates a file birdland.desktop in
~/.local/share/applications to add itself to the system menu.)

The first time you run *Birdland* it
creates a configuration directory, populates
that with a prototype configuration file and several other files, and builds
a database from included raw-index files.

## Upgrade Birdland
Repeat the steps above in *Install Birdland*. On subsequent installations the configuration directory
and contents are preserved.

## Remove Birdland

```
~/.local/share/birdland/birdland/Remove-Birdland.sh
```
