#!/usr/bin/env python

from __future__ import print_function
import importlib
import ortho
from .reporter import call_reporter

"""
MAGIC IMPORTER
Called from automacs/amx/__init__.py to import extension modules and distribute state variables (including 
state, settings, expt) to all extension modules. Also distributes core modules to extension modules and allows
extension modules to override core functionality.
"""

def magic_importer(expt,instruct,**kwargs):
	distribute = kwargs.pop('distribute',{})
	distribute_down = kwargs.pop('distribute_down',True)
	if kwargs: raise Exception('unprocessed kwargs %s'%kwargs)
	outgoing,imported = {},{}
	# process standard imports
	modules = instruct.pop('modules',{})
	for mod_name in modules:
		# use ortho for top-level imports note that this excludes __all__ as desired
		# note that distribute will take every module and find sub-modules and distribute variables there
		# ... which should suffices for most modules i.e. you should only need the state at the very top 
		# ... level of an imported module. see below for a method to distribute variables to all submodules 
		mod = ortho.imports.importer('amx/gromacs',verbose=False,distribute=distribute)
		# only expose functions
		#!!! later expose other objects, classes, etc?
		#!!! washes
		#!!! check for overwrites and note them
		#!!! reporter
		for key,val in mod.items():
			if key in outgoing: raise Exception('dev. refusing to add %s to outgoing again'%key)
			#! python 2 vs 3?
			elif callable(val): outgoing[key] = val
			else: pass
		# manual method to distribute variables down to all submodules. note that importer distribute flag 
		# ... does top level. if ortho ever gets recursive variable distribution that would supercede this
		if distribute_down and distribute:
			import re,sys
			# the module name will always be in the sys.modules list
			sysmods_this = dict([(k,v) for k,v in sys.modules.items() if re.search(mod_name,k)])
			# any system packages are null so we distribute to everything that has a pulse er path
			local_mods = dict([(k,v) for k,v in sysmods_this.items() if v!=None])
			for mod in local_mods:
				for key,val in distribute.items(): 
					setattr(local_mods[mod],key,val)
	initializers = instruct.pop('initializers',None)
	if initializers:
		imported['initializers'] = {}
		for name in initializers:
			if name not in outgoing: raise Exception('cannot find initializer function %s'%name)
			else: imported['initializers'][name] = outgoing[name]
	if instruct: raise Exception('unprocessed instructions %s'%instruct)
	# decorate outgoing functions
	for key,val in outgoing.items():
		outgoing[key] = call_reporter(func=val,state=state)
	imported['functions'] = outgoing
	return imported
