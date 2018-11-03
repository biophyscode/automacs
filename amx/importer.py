#!/usr/bin/env python

from __future__ import print_function
import importlib,sys,re,os
from collections import OrderedDict as odict
import ortho
from ortho.misc import listify
from .reporter import call_reporter

"""
MAGIC IMPORTER
Called from automacs/amx/__init__.py to import extension modules and distribute state variables (including 
state, settings, expt) to all extension modules. Also distributes core modules to extension modules and allows
extension modules to override core functionality.
"""

def distribute_widely(mod_names,distribute):
	"""
	Distribute variables to submodules via sys.modules.
	"""
	local_mod_names = []
	#! note that you must include amx/automacs and amx/reporter in the framework modules for amx but we
	#!   should fix this by tightening up this function so it distributes and exposes as generally as possible
	for mod_name in mod_names:
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
				# we set the functions as attributes to the module so that they are reported in
				#   whichever context they are used. this step distributes and ensures reporting
				#   since we draw distribute functions from the outgoing list
				setattr(local_mods[mod],key,val)
			local_mod_names.append(mod)
	return local_mod_names

def magic_importer(expt,instruct,**kwargs):
	distribute = kwargs.pop('distribute',{})
	distribute_down = kwargs.pop('distribute_down',True)
	if kwargs: raise Exception('unprocessed kwargs %s'%kwargs)
	outgoing,imported = odict(),{}
	# process standard imports
	modules = instruct.pop('modules',[])
	# append extensions to modules
	modules += listify(expt.get('extensions',[]))
	placehelds = []
	local_mod_names = []
	reported_functions,already_reported = [],[]
	distribute_add = []
	listing = {}
	for mod_name in modules:
		# use ortho for top-level imports note that this excludes __all__ as desired
		# note that distribute will take every module and find sub-modules and distribute variables there
		#   which should suffices for most modules i.e. you should only need the state at the very top 
		#   level of an imported module. see below for a method to distribute variables to all submodules 
		mod = ortho.imports.importer(mod_name,verbose=False,distribute=distribute)
		listing[mod_name] = mod
		redistribute = mod.get('_shared_extensions',[])
		# only expose functions
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
			if callable(val): outgoing[key] = val
			else: pass
			if key not in mod.get('_not_reported',[]):
				reported_functions.append(key)
			if key in redistribute:
				if key not in outgoing:
					raise Exception('asked for something that does not exist: %s'%key)
				distribute_add.append(key)
	# before decoration we distribute the items we already have to the modules
	#   so that they have access to e.g. state, settings, etc. this step is
	#   essential for call_reporter, which uses the state to log the functions
	#   to a special log file (step_log_file), and must run as a decorator for
	#   all "reported" functions before they are distributed back to different
	#   modules. for example, we import a gmx function as part of the gromacs
	#   module, it is sent to the call_reporter, the call_reporter needs the
	#   state variable to log it correctly, and then after it is decorated to
	#   write the log file, we send gmx to all of the other modules so it
	#   is universally accessible
	local_mod_names.extend(
		distribute_widely(mod_names=modules,distribute=distribute))
	# at this stage we have collected outgoing functions for the amx global namespace and also 
	#   caught the shared extensions which must be distributed alongside the incoming distribute dict
	#   to all of the other modules
	# decorate outgoing functions
	for key,val in outgoing.items():
		if key in already_reported: continue
		if key not in reported_functions: continue
		if val.__name__=='<lambda>': continue
		#! cannot report class instantiation
		outgoing[key] = call_reporter(func=val)
	# shared extensions are added to distribute after decoration
	for key in distribute_add: distribute[key] = outgoing[key]
	local_mod_names.extend(
		distribute_widely(mod_names=modules,distribute=distribute))
	# collect initializers
	initializers = instruct.pop('initializers',None)
	if initializers:
		imported['initializers'] = {}
		for name in initializers:
			if name not in outgoing: raise Exception('cannot find initializer function %s'%name)
			else: imported['initializers'][name] = outgoing[name]
	imported['functions'] = outgoing
	imported['module_names'] = list(set(local_mod_names))
	return imported

def get_import_instructions(config):
	"""Read import instructions for frameworks from config for amx init."""
	# template for instructions
	instruct = {'modules':[],'decorate':{
		'functions':[],'subs':[]},'initializers':[]}
	frameworks = config.get('frameworks',{})
	for name,frame in frameworks.items():
		for i in ['modules','initializers']:
			instruct[i].extend(frame.get(i,[]))
		decorate = frame.get('decorate',{})
		for i in ['functions','subs']:
			instruct['decorate'][i].extend(decorate.get(i,[]))
	return instruct
