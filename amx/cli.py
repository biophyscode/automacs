#!/usr/bin/env python

"""
AUTOMACS command-line interface
note that amx/runner is included in the config.py commands list to supply prep,clean,go
"""

from __future__ import print_function

# use importer to import any functions which cannot import the entire amx
from ortho.imports import importer

def gromacs_config(*args,**kwargs):
	"""Wrap gromacs_config which is imported outside of the amx import."""
	func = importer('amx/gromacs/configurator.py')['gromacs_config']	
	func(*args,**kwargs)
