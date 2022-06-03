.RECIPEPREFIX = +
# -----------------------------------------------------------------------------------
#   Makefile - WRW 21 Sept 2020
#   For tar and Setuptools

# -----------------------------------------------------------------------------------

#   Everything but the cruft. To reproduce development environment.
#   Exclude src/src because it is redundant as src is symlink to birdland.

tar-dev:
+   cd ..;  tar --exclude ',*' \
+        --exclude '.e*' \
+        --exclude '__pycache__' \
+        --exclude Hold \
+        --exclude src/src \
+        -cvzf ~/Uploads/tar/birdland-dev.tar.gz \
+        Birdland

# -------------------------------------------------------------------
#   Just what is needed to use birdland, most of above but not all and enumerated.

tar-user:
+   cd ..; tar --exclude ',*' \
+       --exclude '.e*' \
+       --exclude '__pycache__' \
+       --exclude 'Icons/Svg' \
+       -czvf ~/Uploads/tar/birdland-user.tar.gz \
+       Birdland/LICENSE \
+       Birdland/src/birdland/birdland.py \
+       $$(ls Birdland/src/birdland/fb_*.py ) \
+       Birdland/src/birdland/fullword*.so \
+       Birdland/src/birdland/build_tables.py \
+       Birdland/src/birdland/diff_index.py \
+       Birdland/src/birdland/Fullword-Match \
+       Birdland/src/birdland/Icons \
+       Birdland/src/birdland/birdland.conf.proto \
+       Birdland/src/Documentation/birdland.pdf \
+       Birdland/src/Documentation/birdland-create.pdf \
+       Birdland/src/Documentation/birdland.md \
+       Birdland/src/birdland/build-pdf-from-image.py \
+       Birdland/src/birdland/get-youtube-links.py \
+       Birdland/src/birdland/ReadMe-Birdland.md \
+       Birdland/src/birdland/Remove-Birdland.sh\
+       Birdland/src/birdland/Package_Type_Unpacked.txt \
+       Birdland/requirements.txt \
+       Birdland/src/Book-Lists \
+       Birdland/src/Canonical \
+       Birdland/src/Index-Sources \
+       Birdland/src/Music-Index \
+       Birdland/src/YouTube-Index \
+       Birdland/ReadMe-Tar.md \
+       Birdland/Install.sh

# ------------------------------
pypi:
+   python -m build --outdir ~/Uploads/setuptools

# ------------------------------
install:
+    pip install $$(ls -t ~/Uploads/setuptools/birdland*.tar.gz | head -1 ) --user                  

# ------------------------------
#   'python -m twine upload' gets username and password from ~/.pypirc
upload:
+   python -m twine upload --repository testpypi \
+        $$(ls -t ~/Uploads/setuptools/birdland*.tar.gz | head -1 ) \
+        $$(ls -t ~/Uploads/setuptools/birdland*-any.whl | head -1 )
