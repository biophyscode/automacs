
"""
Sphinx configuration for ortho.
Run this with `make docs`.
#!!! better location for docs? movable location? custom decision about what goes in the docs?
"""

import sys
import os
import shlex

sys.dont_write_bytecode = True

extensions = ['sphinx.ext.autodoc','numpydoc']

autodoc_docstring_signature = True
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

#! autosummary_generate = True
singlehtml = True

# project information
project = u'amx'
html_show_copyright = False
html_show_sphinx = False
author = u'BioPhysCode'
version = ''
release = ''
language = 'en'
today_fmt = '%Y.%B.%d'
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'
todo_include_todos = False

# paths for custom themes
html_title = "AUTOMACS Documentation"
html_short_title = "AMX docs"
#html_logo = 'logo.png'
#html_theme = 'bizstyle-custom'
#html_theme_path = ['./style']
#html_static_path = ['style']
html_theme = ['bizstyle','alabaster'][0]
htmlhelp_basename = 'amxdoc'

from sphinx.ext import autodoc

class SimpleDocumenter(autodoc.MethodDocumenter):
  objtype = "simple"
  # do not add a header to the docstring
  def add_directive_header(self, sig): pass

def setup(app):
    app.add_autodocumenter(SimpleDocumenter)

# variable paths
#! get these exactly from modules
#! rst_prolog = '\n'.join(['.. |path_runner| replace:: ../../../runner/',])

import os,sys
sys.path.insert(0,os.path.realpath('../../'))
os.chdir('../../')
print(os.getcwd())
import ortho

