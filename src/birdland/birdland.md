# Birdland Musician's Assistant

Birdland is a music reader and library manager for fakebooks and other music books.
It locates and displays a page of music by searching a database of titles and
other metadata.  Answering the *Let's hear how it goes* query it also suggests audio
files, midi files, and YouTube links matching the search. 

A secondary feature of Birdland is index management. Birdland contains tools to harmonize
indexes from disparate sources, compare them, and integrate them into one database.
Birdland ships with index data from eight sources covering over 100 books and over 20,000 titles.
Users can edit existing indexes and add their own.

## Foundational Concepts and Terminology

### No Proprietary Content
Birdland ships with no proprietary content - music, audio or midi. You must supply your
own media, which is available from many online sources.

### Music vs Audio
The common (and ambiguous) terms - *music* and *audio* - are used formally here. You look at *Music* ; you listen to *Audio*. That is, *Music* is derrived from the printed page, *Audio* from performance. The term *Book* is used informally to refer to a *Music* book.

### Title Indexes
A key feature of Birdland is the ability to locate title in a book by searching a database. This requires an index that maps song titles to pages in books. Birdland ships with indexes compiled from several online sources and one which was extracted from the table of contents in books in the author's
music library, having a table of contents.  Each source has a
short, three character name, which is identified as *Src*.  Each source
also has a longer, descriptive name identified as *Source*. You may add indexes you create for books not covered here or ones from other sources.

### Music Identifiers
Every music book has three identifiers.  The *Local Name* is specific
(or local) to each index source and invented by the person compiling the
index. *Local* names are often cryptic and non-unique across different index sources.

The *Canonical Name* is descriptive, is unique over all music books, and
was selected by author of Birdland.

The *File Name* is the name of the music file in your music library.
A file in the configuraiton directory maps between canonical name and file
name.  You can manage that file with a text editor or using a tool in Birdland.
That file must exist before Birdland can find your music files.

### Page vs. Sheet 
Two other common (and also ambiguous) terms, *Page* and *Sheet*, are also used
formally here. The *Page* number of a title is a PDF concept. It is what is shown by PDF readers. The *Sheet* number of a title is what is
shown on the visual page and contained in the index. 
In the general case *Page* and *Sheet* numbers
are not the same and vary by index source. *Page* and *Sheet* numbers
are mapped for each index source by a table known as the *Sheet Offset Table*. It contains
one or more pairs of numbers. Starting at the sheet represented by the first number
the *Page* number is obtained by adding the second number to the sheet number.
For some index sources the *Page* number and *Sheet* number are the same.

## Features
* Locate music by searching for the song title, composer or lyricist from data in the index
and the the title in the music filename. /// CHECK.

* Locate audio by searching for the song title, artist, and album in data
extracted from metadata in the audio files.  Audio file names are not
searched because they normally overlap the metadata.  The titles obtained
from searching the audio index may optional be included in a search of the
music index.  This provides a means of identifying titles by artist and
album metadata, which is in the audio files index but not in the music file index.

* Locate midi by searching for the song title in the midi filename.  Midi
files contain no reliable and uniform metadata so only the filename is
searched.

* Locate YouTube pages by searching a table created by looking up all
titles in the authors library.

* Birdland uses Sqlite3 database by default but can use MySql under command-line
option. To use MySql you must first create a MySql database called *Birdland*.

* Support for use on multiple hosts with a shared configuration with host-specific
sections for settings likely to vary by host.

## Installation

### System Requirements

Birdland requires the Python 3 interpreter. This is likely installed on most modern Linux
distributions, in included in the self-contained package, but will have to be installed
for the tarball and PyPi installation if not already present.

Birdland requires the following Python modules. These are installed automatically if installing
Birdland from PyPi, are included in the self-contained package, but have to be installed manually
when installing Birdland from the tarball.
```
pandas
PySimpleGUI
mysqlclient
PyMuPDF
tk
mutagen
click
configobj
unidecode
```
Birdland also needs an audio file player if you want to play audio files matching a music
title, a PDF viewer if you prefer to use an external one in lieu of the one build in, a
midi player if you want to play midi files, and a web browser for viewing YouTube links.
We have used the *vlc* audio player, tested with the *okular* PDF viewer though we
generally use the build-in one, the *timidity* music player with the *FluidR3_GM.sf2*
soundfount, and the *qutebrowser* browser for its simple, non-distracting user interface.
We have found that the *FluidR3_GM.sf2* soundfont has good coverage of General Midi
instruments and remarkably good samples.

### Tarball (gzip compressed tar file)

### From PyPi

### Bundled package.
Unzip the download into a folder of your choice. Launch the *birdland* executable in that folder.



## Quick Start

### Settings

When Birdland starts for the first time it creates a folder, *.birdland*, in your home
directory (or as specified by the -c confdir option) and copies a default configuration file, *birdland.conf*, a
empty setlist file, *setlist.json*, an empty canonical to file map file, *Canonical2File.txt*, a sample
canonical to file map file, *Example-Canonical2File.txt*, and an empty audio index, *hostname-Audio-Index.json.gz*,
where *hostname* is the name of your host. The hostname is included in the audio index filename to
support running Birdland on multiple hosts, each with a different audio library. The canonical-to-file map file
may be similarly named but is not done so by default.

Birdland then prompts you set up your configuration in the settings menu: *Edit->Settings*. The *birdland.conf* file is an ordinary text file so you can edit it directly with a text editor if you prefer.

There you can tell Birdland the location of your music, audio, and midi libraries.  Each of these is
specified by a root directory and a list of one or more directories under the root.

Birdland needs to know the mapping between the canonical music file names used in the
index and the names of the music files on your system.  You can populate the
canonical-to-file map file using the build-in tool in the *Edit Canonical->File* tab or
with a text editor.  The file consists of one line per music file containing the canonical
name and the music file name separated by a vertical bar.  A reasonably-complete example
is in *Example-Canonical2File.txt* to use as a starting point.  You may find that the file
names in that are quite close to your music file names and only minor edits are needed.

Next click *Tools->Scan Audio Library* if you intend to include your audio library in the
Birdland database.  This can take some time if you have a large audio library, perhaps
around a half-hour for a half-terabyte of audio files. You can defer this until later if
you are anxious to get started. Birdland gives you a second chance if you accidentally click
this item.

Finally click *Tools->Rebuild Database* to build the database from the index data shipped with Birdland and the additional
data you entered above. This typically takes thirty seconds or so.

There are several more options that are not needed to get started. We'll get to those later.

### Operation
Enter a title in the green text box labled *Title* and hit *Enter* or click *Search*.

Birdland searches for *all* the words entered in the order they appear. This is similar, but not identical, to *Fullword Search* supported
by MySql and Sqlite databases.

Birdland searches for the title in the music index, the audio index, in the music filenames,
the midi filenames and the YouTube index and activates the tab for the first match found
in the above order.

Click on a row in the *Music Index* tab to view a title found in the index,
the *Audio Index* to listen to the title found in the index, the *Music Files* tab to view a title
found in the music filename, the *Midi Files* tab to listen to a title found in the midi filename,
and the *YouTube Index* to see the YouTube video for the title found in the YouTube index.

# In Progress...


# History


## Fakebook Index Work - Dec 2021
This paper describes work started around Sept 2020 and resumed in Dec 2021.
It is separate from the Birdland project from 2011 or so and Bluebird from the fall of 2019.


## Index Management
The material in this section is applicable only if you are working at the index source
level. This includes adding a new index source or correcting errors in the indexes shipped with Birdland.


## Input Data

### Index Files

The raw source file is the origin of the index data, that is, a mapping between a song
title, fakebook, and page number.  Presently, we are working with six sources of index
data.

    * AdamSpiers
    * Buffalo
    * MikelNelson
    * Sher
    * Skrivarna
    * Splitter
    * StompBox

### Fakebook Files

This project does not concern itself with the acquisition of fakebooks. We assume that the
user has acquired them, that they live under a common root, and that they have unique names 
but not necessarily the book names that appear in any index nor the canonical book names 
though they could be and sometime are. A few examples:

    * Library of Musicians Jazz.pdf
    * Firehouse Jazz Band Commercial Dixxieland Fake Book.pdf


## Processing

### Source-Specific Processing

For each source there is a python script, do-<source name>.py, in a source-specific
directory.  That script reads the raw data in a source-specific form and writes a
*json* file in a common form in the directory '/home/wrw/Library/FBIndex/Index.Json'. The 
json file is named with a short abbreviation of the source (*source_short* in the code)
and the *local book name*. It contains the:

* Local book name
* Source name
* Title and page number for each song in the book.

A few lines from the file:

```
{
  "book": "ColoBk",
  "source": "AdamSpiers",
  "contents": [
    {
      "title": "Afternoon In Paris",
      "page": "17"
    },
    {
      "title": "Algo Bueno",
      "page": "274"
    },
    {
      "title": "All Blues",
      "page": "18"
    },
```
