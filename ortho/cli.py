#!/usr/bin/env python

"""
ORTHO
Makefile interFACE (makeface) command-line interface
Note that you should debug with `python -c "import ortho;ortho.get_targets(verbose=True,strict=True)"`
"""

from __future__ import print_function

import os,sys,re,importlib,inspect
from .dev import tracebacker
from .misc import str_types,locate
from .config import set_config,setlist,set_list,unset,config,set_dict
from .environments import environ
from .bootstrap import bootstrap
from .imports import importer,glean_functions
from .unittester import unittester
from .reexec import interact

# any functions from ortho exposed to CLI must be noted here and imported above
expose_funcs = {'set_config','setlist','set_list','unset','set_dict','environ',
	'config','bootstrap','interact','unittester','import_check','locate'}
expose_aliases = {'set_config':'set','environ':'env'}

# collect functions once
global funcs,_ortho_keys_exposed
funcs = None

def collect_functions(verbose=False,strict=False):
	"""
	Collect available functions.
	Note that strict in this context only prevents "glean_functions" from being used, and is distinct from
	the strict import scheme in ortho.imports which is used to perform standard pythonic imports.
	"""
	global funcs
	funcs = {}
	# start with the basic utility functions specified at the top
	funcs = dict([(expose_aliases.get(k,k),globals()[k]) for k in expose_funcs])
	sources = conf.get('commands',[])  # pylint: disable=undefined-variable
	# accrue functions over sources sequentially
	for source in sources:
		if os.path.isfile(source) or os.path.isdir(source):
			try: 
				if verbose: print('status','importing source %s'%source)
				mod = importer(source,verbose=verbose)
			# if importing requires env then it is not ready when we get makefile targets
			except Exception as e:
				# debug imports during dev with `ortho.get_targets(verbose=True)`
				if verbose: print('exception',e)
				if os.path.isdir(source):
					raise Exception('failed to import %s '%source+
						'and cannot glean functions because it is not a file')
				elif not strict: 
					funcs.update(**glean_functions(source))
				else:
					from dev import tracebacker
					tracebacker(e)
			else:
				incoming = dict([(k,v) for k,v in mod.items() if callable(v)])
				# remove items if they are not in all
				mod_all = mod.get('__all__',[])
				# also allow __all__ to be temporarily blanked during development
				if '__all__' in mod or mod_all: 
					incoming_exposed = dict([(k,v) for k,v in incoming.items() if k in mod_all])
				else: incoming_exposed = incoming
				if verbose: print('status','trimming source %s to __all__ = %s'%(
					source,incoming_exposed.keys()))
				funcs.update(**incoming_exposed)
		else: raise Exception('cannot locate code source %s'%source)
	# note which core functions are exposed so we can filter the rest
	global _ortho_keys_exposed
	_ortho_keys_exposed = set(funcs.keys())
	# no return because we just refresh funcs in globals
	return

def import_check():
	"""
	Utility which simulates debugging via:
	python -c "import ortho;ortho.get_targets(verbose=True,strict=True)"
	"""
	collect_functions(verbose=True,strict=True)
	print('status','see logs above for import details')
	print('status','imported functions: %s'%funcs.keys())

def get_targets(verbose=False,strict=False):
	"""
	Announce available function names.
	Note that any printing that happens during the make call to get_targets is hidden by make.
	"""
	if not funcs: collect_functions(verbose=verbose,strict=strict)
	targets = funcs
	# filter out utility functions from ortho
	target_names = list(set(targets.keys())-
		(set(_ortho_keys)-_ortho_keys_exposed))  # pylint: disable=undefined-variable
	print("make targets: %s"%(' '.join(sorted(target_names))))

def run_program(_do_debug=False):
	"""
	Interpret the command-line arguments.
	"""
	global funcs
	ignore_flags = ['w','--','s','ws','sw']
	arglist = [i for i in list(sys.argv) if i not in ignore_flags]
	# previously wrote the backend script i.e. makeface.py from the makefile via:
	# ... @test -f makeface.py || echo "$$MAKEFACE_BACKEND" > $(makeface)
	# ... however now we pipe the script in from the environment and chop off the -c flag below
	# incoming arguments include a command (previously a script, makeface.py) which we ignore
	if arglist[0]!='-c':
		raise Exception('argument list must start with the command flag (`-c`) from makefile '
			'however we received %s'%arglist)
	if not arglist: raise Exception('no arguments to parse')
	else: arglist = arglist[1:]
	if arglist[0] in ['set','unset']: funcs = {'set':set_config,'unset':unset}
	elif not funcs: collect_functions()
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	# regex for kwargs. note that the makefile organizes the flags for us
	regex_kwargs = r'^([\w]+)\=(.*?)$'
	while arglist:
		arg = arglist.pop(0)
		if re.match(regex_kwargs,arg):
			parname,parval = re.findall(regex_kwargs,arg)[0]
			kwargs[parname] = parval
		else:
			if sys.version_info<(3,3): 
				#! the following will be removed by python 3.6
				argspec = inspect.getargspec(funcs[funcname])
				argspec_args = argspec.args
			else:
				sig = inspect.signature(funcs[funcname]) # pylint: disable=no-member
				argspec_args = [name for name,value in sig.parameters.items() 
					if value.default==inspect._empty or type(value.default)==bool] # pylint: disable=no-member
			#! note that a function like runner.control.prep which uses an arg=None instead of just an
			#! ...arg will need to make sure the user hasn't sent the wrong flags through.
			#! needs protection
			if arg in argspec_args: kwargs[arg] = True
			else: args.append(arg)
	for k,v in kwargs.items():
		try: kwargs[k] = eval(v)
		except: pass
	# ignore python flag which controls python version
	kwargs.pop('python',None)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))
	# call the function and report errors loudly or drop into the debugger
	call_text = (' with '+' and '.join([str('%s=%s'%(i,j)) 
		for i,j in zip(['args','kwargs'],[args,kwargs]) if j]) 
		if any([args,kwargs]) else '')
	print('status','calling "%s"%s'%(funcname,call_text))
	if funcname not in funcs:
		raise Exception('function `%s` is missing? %s'%(funcname,funcs.keys()))
	# detect ghosted functions and try to import
	if type(funcs[funcname]) in str_types:
		print('error','the function `%s` from `%s` was only inferred and not imported. '
			'this is commonly due to a failure to import the module '
			'because you do not have the right environment'%(funcname,funcs[funcname]))
		print('status','to investigate the problem we will now import the module so you can see the error. '
			'importing %s'%funcs[funcname])
		try: mod = importer(funcs[funcname]) # pylint: disable=unused-variable
		except Exception as e: 
			tracebacker(e)
			print('error','to continue you can correct the script. '
				'you may need to install packages or source add an environment via '
				'`make set activate_env="path/to/activate <env_name>"')
			sys.exit(1)
	# we must check for ipdb here before we try the target function
	try: import ipdb as pdb_this
	except: import pdb as pdb_this
	try:
		funcs[funcname](*args,**kwargs)
	#? catch a TypeError in case the arguments are not formulated properly
	except Exception as e: 
		tracebacker(e)
		if conf.get('auto_debug',_do_debug): # pylint: disable=undefined-variable
			_,value,tb = sys.exc_info()
			pdb_this.post_mortem(tb)
		else: sys.exit(1)
	except KeyboardInterrupt:
		print('warning','caught KeyboardInterrupt during traceback')
		sys.exit(1)
