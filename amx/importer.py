#!/usr/bin/env python

from __future__ import print_function
import importlib,sys,re,os
import ortho
from ortho.misc import listify
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
	modules = instruct.pop('modules',[])
	# append extensions to modules
	modules += listify(expt.get('extensions',[]))
	placehelds = []
	reported_functions = []
	listing = {}
	for mod_name in modules:
		# use ortho for top-level imports note that this excludes __all__ as desired
		# note that distribute will take every module and find sub-modules and distribute variables there
		# ... which should suffices for most modules i.e. you should only need the state at the very top 
		# ... level of an imported module. see below for a method to distribute variables to all submodules 
		mod = ortho.imports.importer(mod_name,verbose=False,distribute=distribute)
		listing[mod_name] = mod
		redistribute = mod.get('_shared_extensions',[])
		# only expose functions
		#!!! later expose other objects, classes, etc? washes? check for overwrites, reporter
		#!!!   note that many of these are now implemented with the reported_functions, redistribute, etc
		for key,val in mod.items():
			"""
			Previously we raised exception if we added the same function to the
			outgoing dictionary twice. This causes problems when we use the same
			ortho tools in different extension modules so it is disabled here.
			Note that the extension modules follow the instruct modules in a
			list so they will always be the most current. Another solution is to
			use the __all__ feature to ensure that only novel functions are 
			imported but this is laborious.
			"""
			#! python 2 vs 3?
			if callable(val): outgoing[key] = val
			else: pass
			if key not in mod.get('_not_reported',[]):
				reported_functions.append(key)
			#! move this to instruct?
			if key in redistribute:
				#! should we have a problem with overwriting
				if key not in outgoing:
					raise Exception('asked for something that no exit: %s'%key)
				distribute[key] = outgoing[key]
		# manual method to distribute variables down to all submodules. note that importer distribute flag 
		# ... does top level. if ortho ever gets recursive variable distribution that would supercede this
		if distribute_down and distribute:
			# the module name will always be in the sys.modules list
			# we use the sys.modules trick whenever we know amx is loaded and we need it from an unusual spot
			# note that we do a substring search on the last word if divided by slashes
			#! should we be more careful here?
			search_str = mod_name.split('/')[-1]
			sysmods_this = dict([(k,v) for k,v in sys.modules.items() if re.search(search_str,k)])
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

	# decorate outgoing functions
	for key,val in outgoing.items():
		if key not in reported_functions: continue
		#! cannot report class instantiation
		outgoing[key] = call_reporter(func=val,state=state)
	imported['functions'] = outgoing
	return imported
