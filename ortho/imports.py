#!/usr/bin/env python

from __future__ import print_function
import os,sys

def strip_builtins(mod):
	"""
	Remove builtins from a hash in-place and elevate functions to keys.
	"""
	obj = mod.__dict__
	if '__all__' in obj.keys(): keys = obj['__all__']
	else: keys = [key for key in obj.keys() if not key.startswith('__')]
	# let the user tell us which functions to hide or ignore
	hidden = obj.pop('_not_all',[])
	for h in hidden:
		if h not in keys: raise Exception('_not_all asks to hide %s but it is absent'%h)
		keys.remove(h)
	if '_not_all' in keys: keys.remove('_not_all')
	# if you pop __builtins__ here then the imported functions cannot do essentials e.g. print
	# .. so instead we pass along a copy of the relevant functions for the caller
	return dict([(key,obj[key]) for key in keys])

def remote_import_script(source):
	"""
	Import the functions in a single script.
	This code is cross-compatible with python2.7-3.6 and we use it because there is basically no way to do 
	this from the standard library.
	"""
	mod = {}
	with open(source) as f:
		code = compile(f.read(),source,'exec')
		exec(code,globals(),mod)
	return mod

def remote_import_module(source):
	"""
	Remotely import a module.
	Note that we call this from the importer after trying the standard importlib.import_module.
	Since that module can handle imports in the path, we only continue if the basename is not in the path.
	"""
	if os.path.realpath(os.path.dirname(source)) in map(os.path.realpath,sys.path):
		raise Exception(('refusing to remotely import %s because its parent is already in the path '
			'and hence it should be imported with importlib.import_module instead via importer')%source)
	# manipulate paths for remote import
	original_path = list(sys.path)
	sys.path.insert(0,os.path.dirname(source))
	import importlib
	mod = importlib.import_module(os.path.basename(source),package=os.path.dirname(source))
	sys.path = list(original_path)
	# we return modules as dictionaries
	return strip_builtins(mod)

def importer(source,verbose=False):
	"""
	Route import requests according to type.
	We always return the module dictionary because the fallback remote_import_script must run exec.
	Testing notes:
	- import a local script directly with import_module
	- import a local script manually using exec
	- import a local module with import_module
	- import a remote module by manipulating and resetting the path
		
	"""
	source_full = os.path.expanduser(os.path.abspath(source))
	# get paths for standard import method
	if os.path.isfile(source_full): 
		fn,dn = os.path.splitext(os.path.basename(source_full))[0],os.path.dirname(source_full)
	else: fn,dn = os.path.basename(source_full),os.path.dirname(source_full)
	# standard import method
	try:
		if verbose: print('status','standard import for %s'%source)
		import importlib
		mod = importlib.import_module(fn,package=dn)
		# always return the module as a dictionary
		return strip_builtins(mod)
	except: 
		if verbose: print('warning','standard import failed')
		# import the script remotely if import_module fails above
		if os.path.isfile(source_full): 
			if verbose: print('status','remote_import_script for %s'%source)
			return remote_import_script(source_full)
		# import the module remotely
		else: 
			if verbose: print('status','remote_import_module for %s'%source)
			return remote_import_module(source_full)

def glean_functions(source):
	"""
	In rare cases we need funciton names before the environment is ready so we parse without executing.
	Note that this method does not use __all__ to filter out hidden functions.
	Users who want to use this to get make targets before the environment should just write a single 
	script with the exposed functions since __all__ is not available.
	"""
	import ast
	with open(source) as fp:
		code = fp.read()
		tree = ast.parse(code)
	function_gleaned = [i.name for i in tree.body if i.__class__.__name__=='FunctionDef']
	return dict([(i,str(source)) for i in function_gleaned])
