#!/usr/bin/env python

from __future__ import print_function
import os,sys,re,importlib,glob

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

def remote_import_script(source,distribute=None):
	"""
	Import the functions in a single script.
	This code is cross-compatible with python2.7-3.6 and we use it because there is basically no way to do 
	this from the standard library.
	"""
	mod = {}
	#! check whether this is working?
	if distribute: mod.update(**distribute)
	with open(source) as f:
		code = compile(f.read(),source,'exec')
		exec(code,mod,mod)
	return mod

def distribute_to_module(mod,distribute):
	"""
	Distribute a builtin-esque variable to a module and to one level of its submodules.
	Development note: 
	This method distributes variables to the top level of a module but no deeper. The automacs
	magic_importer method will go one step further and use some conservative inference on sys.modules to 
	distribute the variables to all submodules automatically. However, it would be slightly more elegant 
	to recursively collect modules and distribute automatically without using sys.modules (or worse,
	builtins). If a recursive method is developed, the `distribute_down` method can be removed from the
	automacs magic importer.
	"""
	# distribute to the top level
	for key,val in distribute.items(): setattr(mod,key,val)
	#! note that this will not distribute below the top level
	for key in mod.__dict__.keys():
		#! conservative? I think everything has a class and name
		if hasattr(mod.__dict__[key],'__class__') and hasattr(mod.__dict__[key].__class__,'__name__'):
			if mod.__dict__[key].__class__.__name__=='module':
				for varname,var in distribute.items():
					setattr(mod.__dict__[key],varname,var)

def remote_import_module(source,distribute=None):
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
	# removed a try/except message that handled the old "attempted relative import beyond toplevel" issue
	mod = importlib.import_module(os.path.basename(source),package=os.path.dirname(source))
	if distribute: distribute_to_module(mod,distribute)
	sys.path = list(original_path)
	# we return modules as dictionaries
	return strip_builtins(mod)

def import_strict(fn,dn,verbose=False):
	"""Standard importer with no exceptions for importing the local script.py."""
	if verbose: print('note','importing (importlib, strict) from %s: %s'%(dn,fn))
	mod = importlib.import_module(fn,package=dn)
	if verbose: print('note','successfully imported')
	return mod

def importer(source,verbose=False,distribute=None,strict=False):
	"""
	Route import requests according to type.
	We always return the module dictionary because the fallback remote_import_script must run exec.
	We only use the exec in the remote script importer if absolutely necessary. To avoid this we try
	several different uses of importlib.import_module beforehand. The remote script importer makes it possible
	to include scripts at any location using the commands flag in the config managed by ortho.conf which can
	be useful in some edge cases.
	!!! Testing notes:
	- import a local script directly with import_module
	- import a local script manually using exec
	- import a local module with import_module
	- import a remote module by manipulating and resetting the path
	"""
	if not distribute: distribute = {}
	# include __file__ which is otherwise absent when we import this way
	distribute['__file__'] = source 
	source_full = os.path.expanduser(os.path.abspath(source))
	# get paths for standard import method
	if os.path.isfile(source_full): 
		fn,dn = os.path.splitext(os.path.basename(source_full))[0],os.path.dirname(source_full)
	else: fn,dn = os.path.basename(source_full),os.path.dirname(source_full)
	if strict: return import_strict(fn,dn,verbose=verbose)
	# standard import method
	try:
		if verbose: print('status','standard import for %s'%source)
		try:
			if verbose: print('note','importing (importlib) from %s: %s'%(dn,fn))
			mod = importlib.import_module(fn,package=dn)
			if verbose: print('note','successfully imported')
		# try import if path is in subdirectory
		# note that we have to use the fn_alt below if we don't want to perturb paths
		except Exception as e1:
			rel_dn = os.path.relpath(dn,os.getcwd())
			# if the path is a subdirectory we try the import with dots
			if os.path.relpath(dn,os.getcwd())[:2]!='..':
				fn_alt = '%s.%s'%(re.sub(os.path.sep,'.',rel_dn),fn)
				if verbose: 
					print('note','previous exception was: %s'%e)
					print('note','importing (local) from %s'%(fn_alt))
				mod = importlib.import_module(fn_alt,package='./')
			else: 
				#!? print('go up to next try?')
				raise Exception(e1)
		if distribute: distribute_to_module(mod,distribute)
		# always return the module as a dictionary
		return strip_builtins(mod)
	# fallback methods for importing remotely
	except Exception as e2: 
		if verbose: 
			print('warning','standard import failed for "%s" at "%s"'%(fn,dn))
			print('exception',e2)
		# import the script remotely if import_module fails above
		if os.path.isfile(source_full): 
			if verbose: print('status','remote_import_script for %s'%source)
			return remote_import_script(source_full,distribute=distribute)
		# import the module remotely
		elif os.path.isdir(source_full): 
			if verbose: print('status','remote_import_module for %s'%source)
			return remote_import_module(source_full,distribute=distribute)
		else: 
			# note that you get this exception if you have a syntax error 
			#   in amx core functionality for various reasons
			#   and it is often useful to check exceptions e1,e2 above
			raise Exception('cannot find %s'%source)

def glean_functions(source):
	"""
	In rare cases we need function names before the environment is ready so we parse without executing.
	Note that this method does not use __all__ to filter out hidden functions.
	Users who want to use this to get make targets before the environment should just write a single 
	script with the exposed functions since __all__ is not available.
	The purpose of this function is to expose functions even if the script cannot be executed.
	Every time we run make, we check config.json for commands and import those scripts. If some scripts
	have dependencies not available on one system, but we want to run a less needy script, we can still
	see the full complement of functions. Hence the available functions do not change even if only
	a subset can be executed.
	"""
	import ast
	with open(source) as fp:
		code = fp.read()
		tree = ast.parse(code)
	# note that this fails if you import a function because we are using ast
	#   to avoid that you should wrap the imported function so we can identify it as a function
	function_gleaned = [i.name for i in tree.body if i.__class__.__name__=='FunctionDef']
	return dict([(i,str(source)) for i in function_gleaned])
