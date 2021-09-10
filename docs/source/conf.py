# -*- coding: utf-8 -*-
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from reentry import manager
manager.scan()

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import pathlib
import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

# Symlink the examples directory to be in this working directory
source = pathlib.Path(__file__).parent.parent.parent / 'examples'
target = pathlib.Path(__file__).parent / 'examples'
target.symlink_to(source)


import aiida_ase

# -- Project information -----------------------------------------------------

project = 'aiida-ase'
copyright = '2020-2021, ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE (Theory and Simulation of Materials (THEOS) and National Centre for Computational Design and Discovery of Novel Materials (NCCR MARVEL)), Switzerland'
release = aiida_ase.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx_copybutton', 'autoapi.extension', 'sphinx_click']

# Settings for the `sphinx_copybutton` extension
copybutton_selector = 'div:not(.no-copy)>div.highlight pre'
copybutton_prompt_text = r'>>> |\.\.\. |(?:\(.*\) )?\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: '
copybutton_prompt_is_regexp = True

# Settings for the `autoapi` extension
autoapi_dirs = ['../../aiida_ase']
autoapi_ignore = ['*cli*']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_css_files = ['aiida-custom.css']
html_theme_options = {
    'home_page_in_toc': True,
    'repository_url': 'https://github.com/aiidaplugins/aiida-ase',
    'repository_branch': 'master',
    'use_repository_button': True,
    'use_issues_button': True,
    'path_to_docs': 'docs',
    'use_edit_page_button': True,
    'extra_navbar': ''
}
html_domain_indices = True
