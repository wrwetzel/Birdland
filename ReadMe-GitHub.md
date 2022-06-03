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


## Install Required Modules

Go to the directory created when you cloned or unpacked the zip file:
```
cd Birdland
```

Birdland includes a *requirements.txt* file that is suitable for most users.
Uncomment the *mysqlclient* line if you want to use MySql instead of Sqlite3.

Install Python modules under your home directory. Does not require root access.
```
pip install -r requirements.txt --user
```

Or install them system wide. Requires root access.
```
pip install -r requirements.txt
```

You may encounter some Linux-distribution-specific rough edges in setting up Birdland and its requirements.
Be sure to see the *Troubleshooting* section in the documentation.

## Installation

The included installation script *Install.sh* installs
Birdland under *~/.local*, that is, under *.local* in your home directory.  This
creates a directory, *~/.local/birdland*, containing the Birdland executables, raw indexes, canonical
names, and many other directories and files.  It also creates links in *~/.local/bin* to the
executables in *~/.local/birdland*.

Be sure that ~/.local/bin is in your PATH environment variable. If your shell is bash then
check your ~./bashrc file:

```
PATH=~/.local/bin:$PATH
```

### Install from Clone
Go to the directory where you cloned Birdland:
```
cd Birdland
./Install.sh
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
./Install.sh
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

For example, if cloned in ~/tmp:
```
PATH=~/tmp/Birdland/src/birdland:$PATH
```

Or, if unzipped in ~/tmp:
```
PATH=~/tmp/Birdland-main/src/birdland:$PATH
```

The executable is:
```
birdland.pl
```

## Initial Run
Birdland creates a file *birdland.desktop* in
~/.local/share/applications to add itself to the system menu. 

After you run it for the first time from the command line you can then run it
from the system menu. 

The first time you run *Birdland* it creates a configuration directory, populates that with a
prototype configuration file and several other files, and builds a database from included raw-index
files.

## Next Steps

Go to *File->Settings* to configure the location of your music, audio, midi, ChordPro,
and JJazzLab libraries as applicable and your preferred external viewers and players.

Be sure to also configure the *Canonical->File map file(s)* and
Editable *Canonical->File map file* settings.

Birdland needs to know the mapping between canonical music file names and *your* music files.
Use the tool in the *Edit Canonical->File* tab or
edit Canonical2File.txt in your configuration directory possibly using Example-Canonical2File.txt
as a starting point.

With the settings configured scan your audio library and then rebuild the database.
Large audio libraries take a long time to scan so you may want to defer that if you are anxious
to get started.
```
Database -> Scan Audio Library
Database -> Rebuild All Tables
```
See the documentation for more configuration details.

## Upgrade Birdland
Repeat the steps above in *Install Birdland*. On subsequent installations the configuration directory
and contents are preserved.

## Remove Birdland
```
~/.local/share/birdland/birdland/Remove-Birdland.sh
```
