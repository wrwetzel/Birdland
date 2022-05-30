# Install Birdland from GitHub

This information supplements the primary Birdland documentation for
installation only from GitHub. Be sure to also see the primary
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

## Obtain Birdland
You may obtain Birdland from GitHub in two ways, by cloning the Birdland remote repository or by downloading
a .zip file.

### Obtain from Clone
Go to a directory where you will clone it.
```
git clone https://github.com/wrwetzel/Birdland.git
```
This places the birdland package in a directory named *Birdland*.

### Obtain ZIP File from GitHub
Go to: 
```
https://github.com/wrwetzel/Birdland.git
```
Click on the green *Code* button and then *Download ZIP* to download *Birdland-main.zip*. For example,
here we assume it is in the *Downloads* directory in your home directory.

Go to a directory where you will unpack Birdland and unpack it. For example here we assume that is
*tmp* in your home directory.
```
cd ~/tmp
tar -xzvf ~/Downloads/Birdland-main.zip
```
This creates a new directory, *Birdland-main*, containing the package files.                         

## Installation

The included installation script *Install-From-GitHub.sh* installs
Birdland under *~/.local*, that is, under *.local* in your home directory.  This
creates a directory, *~/.local/birdland*, containing the Birdland executables, raw indexes, canonical
names, and many other directories and files.  It also creates links in *~/.local/bin* to the
executables.

Be sure that ~/.local/bin is in your PATH environment variable. If your shell is bash then
check your ~./bashrc file:

```
PATH=~/.local/bin:$PATH
```

### Install from Clone
Go to the directory where you cloned Birdland:
```
cd Birdland
./Install-From-GitHub.sh
```
Since you cloned it you may want to keep the cloned files to explore and modify.       
If not, you may remove them:
```
rm -rf ~/tmp/Birdland-main
```

### Install from ZIP File

Go to the directory where you unpacked Birdland and run the installation script:
```
cd Birdland-main
./Install-From-GitHub.sh
```
You may now remove the package folder in the temporary directory.
```
rm -rf ~/tmp/Birdland-main
```

## Run Birdland
The name of the executable is *birdland*. Run it from the command line:

```
birdland
```

## Alternative to Installation
Instead of installing in *~/.local* you may run birdland directly in the cloned or
unzipped directory hierarchy using the data files also in the hierarchy. In this
case it will be convenient to add the directory containing the executables to your
PATH. 

If cloned in ~/tmp:
```
PATH=~/tmp/Birdland/src/birdland:$PATH
```

If unzipped in ~/tmp:
```
PATH=~/tmp/Birdland-main/src/birdland:$PATH
```

The executables are:
```
birdland.pl
build_tables.pl
diff_index.pl
```

## Initial Run
Birdland creates a file *birdland.desktop* in
~/.local/share/applications to add itself to the system menu. 

After you run it for the first time from the command line you can then run it
from the system menu. 

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
