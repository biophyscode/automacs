#!/usr/bin/env PYTHONDONTWRITEBYTECODE=1 python

"""
ORTHO
Makefile interFACE (makeface) command-line interface
"""

from __future__ import print_function

import os,sys,re,importlib,inspect
from .dev import tracebacker
from .misc import str_types
from .config import set_config,setlist,unset,config,set_hash
from .environments import manage
from .bootstrap import bootstrap
from .imports import importer,glean_functions

# any functions from ortho exposed to CLI must be noted here and imported above
expose_funcs = {'set_config','setlist','unset','set_hash','manage','config','bootstrap'}
expose_aliases = {'set_config':'set'}

# collect functions once
global funcs,_ortho_keys_exposed
funcs = None

def collect_functions():
	"""
	Collect available functions.
	"""
	global conf # from __init__.py
	global funcs
	funcs = {}
	# start with the basic utility functions specified at the top
	funcs = dict([(expose_aliases.get(k,k),globals()[k]) for k in expose_funcs])
	sources = conf.get('commands',[])
	from .config import set_config,setlist,unset
	# accrue functions over sources sequentially
	for source in sources:
		if os.path.isfile(source) or os.path.isdir(source):
			try: mod = importer(source)
			# if importing requires env then it is not ready when we get makefile targets
			except: funcs.update(**glean_functions(source))
			else:
				incoming = dict([(k,v) for k,v in mod.items() if callable(v)])
				# remove items if they are not in all
				mod_all = mod.get('__all__',[])
				if mod_all: incoming_exposed = dict([(k,v) for k,v in incoming.items() if k in mod_all])
				else: incoming_exposed = incoming
				funcs.update(**incoming_exposed)
		else: raise Exception('cannot locate code source %s'%source)
	# note which core functions are exposed so we can filter the rest
	global _ortho_keys_exposed
	_ortho_keys_exposed = set(funcs.keys())
	# no return because we just refresh funcs in globals
	return

def get_targets():
	"""
	Announce available function names.
	"""
	global _ortho_keys # from __init__.py
	if not funcs: collect_functions()
	targets = funcs
	# filter out utility functions from ortho
	print(funcs)
	target_names = list(set(targets.keys())-(set(_ortho_keys)-_ortho_keys_exposed))
	print("make targets: %s"%(' '.join(sorted(target_names))))

def run_program(_do_debug=False):
	"""
	Interpret the command-line arguments.
	"""
	global funcs
	if not funcs: collect_functions()
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
				sig = inspect.signature(funcs[funcname])
				argspec_args = [name for name,value in sig.parameters.items() 
					if value.default==inspect._empty or type(value.default)==bool]
			#! note that a function like runner.control.prep which uses an arg=None instead of just an
			#! ...arg will need to make sure the user hasn't sent the wrong flags through.
			#! needs protection
			if arg in argspec_args: kwargs[arg] = True
			else: args.append(arg)
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
		try: mod = importer(funcs[funcname])
		except Exception as e: 
			tracebacker(e)
			print('error','to continue you can correct the script. '
				'you may need to install packages or source add an environment via '
				'`make set activate_env="path/to/activate <env_name>"')
			sys.exit(1)
	# we must check for ipdb here before we try the target function
	try: import ipdb as pdb_this
	except: import pdb as pdb_this
	try: funcs[funcname](*args,**kwargs)
	#? catch a TypeError in case the arguments are not formulated properly
	except Exception as e: 
		tracebacker(e)
		if conf.get('auto_debug',_do_debug):
			typ,value,tb = sys.exc_info()
			pdb_this.post_mortem(tb)
		else: sys.exit(1)
	except KeyboardInterrupt:
		print('warning','caught KeyboardInterrupt during traceback')
		sys.exit(1)
