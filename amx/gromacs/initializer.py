#!/usr/bin/env python

_not_reported = ['gromacs_initializer']

def gromacs_initializer():
	"""
	This function runs whenever gromacs is loaded.
	Note that we currently use the @gmx_call hook to set the location of gromacs.
	The gromacs_initializer function is set in the framework for automacs and runs every time.
	"""
	#! added this to _not_reported because nothing happens right now
	return
