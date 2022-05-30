.RECIPEPREFIX = +
# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

DEST      = wrwetzel.com:www/Birdland
LOCALDEST = /home/wrw/Uploads/documentation/

PHPMailer = \
PHPMailer-master/src/PHPMailer.php \
PHPMailer-master/src/OAuth.php \
PHPMailer-master/src/POP3.php \
PHPMailer-master/src/SMTP.php \
PHPMailer-master/src/Exception.php  

LANDING = landing.html screenshots.html contact.php contact.html Images $(PHPMailer) \
    download.html

# READMES = ../../ReadMe-Tar.md ../../ReadMe-GitHub.md ../../ReadMe-PyPi.md ../ReadMe-Nuitka.md ../ReadMe-PyInstaller.md
READMES = ../../ReadMe-Tar.md ../../ReadMe-GitHub.md 
PACKAGES = ~/Uploads/tar/birdland-user.tar.gz

MDFILES=\
birdland.md

# Put it first so that "make" without argument is like "make help".

help:
+ @$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).

local:
+ TARGET=local sphinx-build -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
+ rsync -avR --exclude ',*' --exclude={'.es1','.ek1','.ec1'} _build/* $(LOCALDEST)

# + rsync -avR --exclude ',*' --exclude={'.es1','.ek1','.ec1'} _build/* _static/* $(LOCALDEST)

remote:
+ TARGET=production sphinx-build -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
+ rsync -avR --exclude ',*' --exclude={'.es1','.ek1','.ec1'} _build/* _static/* $(DEST)

site:
+ rsync -avR $(LANDING) $(DEST)
+ rsync -av $(PACKAGES) $(READMES) $(DEST)/Downloads

#   Output was awful
#       pdf:
#       + TARGET=production sphinx-build -b pdf "$(SOURCEDIR)" "$(BUILDDIR)"

#   Never saw output
# pdf:
# + TARGET=production sphinx-build -M latexpdf "$(SOURCEDIR)" "$(BUILDDIR)"


pdf:
+ markdown-pdf \
    -o Test-Tutorial.pdf \
    -s /home/wrw/.config/Typora/themes/newsprint.css \
    -f Letter \
    $(MDFILES)
