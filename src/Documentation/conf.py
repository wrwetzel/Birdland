# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os

# import sys
# print( sys.path)

# import sys
# sys.path.insert(0, os.path.abspath('.'))

# import sphinx_rtd_theme
# import lsst_sphinx_bootstrap_theme
# import sphinx_catalystcloud_theme
# from PSphinxTheme import utils

import logilab_sphinx_themes

# -- Project information -----------------------------------------------------

project = 'Birdland'
copyright = '2022'
author = 'Bill Wetzel'

# The full version, including alpha/beta/rc tags
release = '1.0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'recommonmark',
#   'sphinx_rtd_theme',
    'logilab_sphinx_themes',
    'sphinx_markdown_tables',
#   'rst2pdf.pdfbuilder',
    'sphinxcontrib.fulltoc',
#   'sphinxcontrib.googleanalytics',
#   'sphinx.ext.mathjax',   (Didn't work, probably because equation in markdown)
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'ReadMe.txt', ',*', '*.bak', 'custom.css',
                 'Parts.txt',
                 'birdland-create.*',
                 'birdland.pdf', 'birdland.html', 
                 'PHPMailer-master',
                 ]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

# html_theme = 'alabaster'
# html_theme = 'pyramid'
# html_theme = 'traditional'
# html_theme = 'nature'

#   Logilab
#   pip install logilab-sphinx-themes --user

html_theme = 'logilab'        # *** pretty good and has logo
# html_theme = 'sphinx_rtd_theme'        # *** pretty good and has logo

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

html_static_path = ['_static']

source_suffix = {                                                                                                    
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}


# -------------------------------------------------------------
#   WRW 19 Aug 2020 - Changing to a custom landing page.
#   mv index.rst contents.rst

# master_doc = 'contents'
# html_additional_pages = { 'index': 'index.html' }

# -------------------------------------------------------------

source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

target = os.environ[ 'TARGET' ]

#   For Logilab
if html_theme == 'logilab':
    if False:
        if target == 'production':
            html_theme_options = {
                'logo' :  'Full-Logo.png',
                'logo_url' : 'https://pogoanalytics.org',
                # 'sticky_navigation' : False,
            }
        else:
            html_theme_options = {
                'logo' :  'Full-Logo.png',
                'logo_url' : 'https://test.pogoanalytics.org',
                # 'sticky_navigation' : False,
            }

    else:
        html_theme_options = {
            'logo' :  'Top-Logo.png',                               # Gets it from _static/Top-Logo.png
            'logo_url' : 'https://birdland.wrwetzel.com',
        }

html_show_sourcelink = False
html_show_sphinx = False
html_use_index = False

#   Edit custom.css file in:
#       _build/html/_static/custom.css

# html_context = {
#     'css_files': ['_static/custom.css'],
# }

html_css_files = [
    'css/custom.css'
]

# html_logo = 'Images/possum-blue-red-152x152.png'

# if target == 'production':
#     googleanalytics_id = 'UA-73647715-7'

# else:
#     googleanalytics_id = 'UA-73647715-6'
