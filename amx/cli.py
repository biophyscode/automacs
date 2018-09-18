#!/usr/bin/env python

"""
AUTOMACS command-line interface
note that amx/runner is included in the config.py commands list to supply prep,clean,go
"""

from __future__ import print_function

import os
import ortho
# use importer to import any functions which cannot import the entire amx
from ortho.imports import importer
from ortho import conf,bash
from ortho.requires import requires_program
import ortho.modules

def gromacs_config(*args,**kwargs):
	"""Wrap gromacs_config which is imported outside of the amx import."""
	func = importer('amx/gromacs/configurator.py')['gromacs_config']	
	func(*args,**kwargs)

def setup(name):
	"""
	Run this after cloning a fresh copy of automacs in order to clone some standard tools.
	So-called "kickstarters" are recipes for changing the config to specify which modules should be loaded.
	After the configuration is updated we call a function to confirm that the modules are loaded.
	"""
	global conf
	kicks = conf.get('kickstarters',{})
	if name not in kicks:
		raise Exception('cannot find kickstarter named %s in available kickstarters: %s'%(
			name,kicks.keys()))
	# run each command in bash
	for line in kicks[name].splitlines():
		if line.strip(): 
			print('[SETUP]','%s'%line)
			bash(line)
	conf = ortho.read_config()
	# use ortho modules sync to ensure fresh codes
	ortho.modules.sync(modules=conf.get('modules',{}))


def help():
	"""Nice view of the commands."""
	#! needs filtered
	#! need to add a standard help mechanism to ortho that includes a README so leaving this in amx for now.
	from ortho.cli import funcs
	from ortho import treeview
	treeview(dict(commands=funcs.keys()))
	treeview(dict(commands=dict([(i,j.__module__) for i,j in funcs.items() if hasattr(j,'__module__')])))
	import pdb;pdb.set_trace()

def watch():
	"""
	Wrapper for a command which tails the oldest mdrun command.
	"""
	#! reformulate this to use the bash watch function to watch the most current file
	#!   and try using @requires_program('watch')
	# original command works well for watching the last mdrun but doesn't monitor the files
	cmd = 'find ./ -name "log-mdrun*" | xargs ls -ltrh | tail -n 1 | awk \'{print $9}\' | xargs tail -f'
	os.system(cmd)
