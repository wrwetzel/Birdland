.RECIPEPREFIX = +
# -----------------------------------------------------------------------------------
#   Makefile - WRW 21 Sept 2020
#   For Nuitka and PyInstaller
# -----------------------------------------------------------------------------------
# +       --output-dir=~/Uploads/nuitka didn't work, '~' not expanded.

#   Remember, this is run in birdland (cd birdland; below). '../' references
#       are to this directory, where packaging-specific files and data directories live.
#       No additional configuration files for Nuitka build.
# +       --include-data-file=birdland.md=birdland.md \
# +       --include-data-file=birdland.pdf=birdland.pdf \

nuitka:
+   cd birdland; \
+   python -m nuitka \
+       --standalone \
+       --enable-plugin=tk-inter \
+       --include-data-file=birdland.conf.proto=birdland.conf.proto \
+       --include-data-file=ReadMe-Birdland.md=ReadMe-Birdland.md \
+       --include-data-file=Remove-Birdland.sh=Remove-Birdland.sh \
+       --include-data-file=../Package_Type_Nuitka.txt=Package_Type_Nuitka.txt \
+       --include-data-file=../Install-From-Nuitka.sh=Install-From-Nuitka.sh \
+       --include-data-file=../ReadMe-Nuitka.md=ReadMe-Nuitka.md \
+       --include-data-dir=../Documentation=Documentation \
+       --include-data-dir=Icons=Icons \
+       --include-data-dir=../Book-Lists=Book-Lists \
+       --include-data-dir=../Canonical=Canonical \
+       --include-data-dir=../Music-Index=Music-Index \
+       --include-data-dir=../Index-Sources=Index-Sources \
+       --include-data-dir=../YouTube-Index=YouTube-Index \
+       --output-dir=/home/wrw/Uploads/nuitka \
+       birdland.py

# ------------------------------------------------------------
#   Build with PyInstaller for PyPi install.
#   This uses the birdland-partial.spec configuration file.

freeze-partial:
+   pyinstaller \
+       --distpath ~/Uploads/pyinstaller/dist \
+       --workpath ~/Uploads/pyinstaller/build \
+       --name birdland \
+       --noconfirm \
+       --clean \
+       birdland-partial.spec

# ------------------------------------------------------------
#   Didn't get this multi-application build working
# freeze-full:
# +   pyinstaller \
# +       --distpath ~/Uploads/pyinstaller/dist \
# +       --workpath ~/Uploads/pyinstaller/build \
# +       --name birdland \
# +       --noconfirm \
# +       --clean \
# +       birdland-full.spec

# specs:
# +    pyi-makespec --specpath SpecFiles src/check-offsets.py
# +    pyi-makespec --specpath SpecFiles src/build-tables.py

# ------------------------------
