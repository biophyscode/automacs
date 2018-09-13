#!/usr/bin/env python

"""
Sphinx configuration for ortho.
Run this with `make build_docs`.
Codes with multiple documentation sources must set docs in config to render
each documentation source into a new folder.
"""

import sys,os,shlex

sys.dont_write_bytecode = True

extensions = ['sphinx.ext.autodoc','sphinx.ext.intersphinx','numpydoc']

autodoc_docstring_signature = True
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

# project information
project = u'amx'
html_show_copyright = False
html_show_sphinx = False
author = u'BioPhysCode'
version = ''
release = ''
language = 'en'
today_fmt = '%Y.%B.%d'
exclude_patterns = ['_build','Thumbs.db','.DS_Store']
pygments_style = 'sphinx'
todo_include_todos = False

# paths for custom themes
html_title = "ortho Documentation"
html_short_title = "ortho docs"
html_theme = 'bizstyle'
htmlhelp_basename = 'ortho-doc'

from sphinx.ext import autodoc

class SimpleDocumenter(autodoc.MethodDocumenter):
  objtype = "simple"
  # do not add a header to the docstring
  def add_directive_header(self, sig): pass

def setup(app):
  app.add_autodocumenter(SimpleDocumenter)

import os,sys
sys.path.insert(0,os.path.realpath('../../'))
os.chdir('../../')
print(os.getcwd())
import ortho
