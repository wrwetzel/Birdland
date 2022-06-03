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

## Unpack Birdland

Unpack the birdland tar file *birdland-user.tar.gz* in a temporary directory. For example, if you
have *tmp* in you home directory and have downloaded the tar file into *~/Downloads*:
```
cd ~/tmp
tar -xzvf ~/Downloads/birdland-user.tar.gz
```
This creates a new directory, *Birdland*, containing the package files. 

## Install Required Modules

Go to the directory created when you unpacked the tar file:
```
cd ~/tmp/Birdland
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

## Install Birdland

Go to the directory created when you unpacked the tar file and run the installation script:

```
cd ~/tmp/Birdland
./Install.sh
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

The executable is:
```
birdland.pl
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

## Next Steps

Go to *File->Settings* to configure the location of your music, audio, midi, ChordPro,
and JJazzLab libraries as applicable and your preferred external viewers and players.

Be sure to also configure the *Canonical->File map file(s)* and
Editable *Canonical->File map file* settings.

Birdland needs to know the mapping between canonical music file names and *your* music files.
Use the tool in the *Edit Canonical->File* tab or
edit Canonical2File.txt in your configuration directory possibly using Example-Canonical2File.txt
as a starting point.

With the settings configured optionally scan your audio library and then rebuild the database.
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
