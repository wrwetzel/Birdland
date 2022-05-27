# Install Birdland from Tarfile Distribution

If you are reading this you have already unpacked the birdland-user.tar.gz file into a temporary
directory.

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
Install them system wide. Requires root access:
```
pip install click configobj Levenshtein mutagen mysqlclient pandas pillow 
pip install PyMuPDF PySimpleGUI pytesseract tk unidecode youtubesearchpython
```

Or install them under your home directory. Does not require root access.
```
pip install click configobj Levenshtein mutagen mysqlclient pandas pillow --user
pip install PyMuPDF PySimpleGUI pytesseract tk unidecode youtubesearchpython --user
```

The PySimpleGUI Python module requires both tk and tkinter.
It may be automatically installed when you install PySimpleGUI. If not then:

Install tkinter on Ubuntu:
```
    sudo apt-get install python3-tk
```

## Install birdland:

```
cd Birdland
Install-From-Tar.sh
```
This copies data folders to ~/.local/share/birdland and links executables to ~/.local/bin,
which should be in your PATH environment variable.
It may add an entry to your system menu for birdland.

The name of the executable is *birdland*.

You may now remove the unpacked folder in the temporary directory.

## Remove birdland:

```
~/.local/share/birdland/birdland/Remove-Birdland.sh
```
