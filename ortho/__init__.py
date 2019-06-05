#!/usr/bin/env python

"""
ORTHO MODULE DOCSTRING
"""

from __future__ import print_function
import os,sys,re,subprocess
from .misc import str_types
_init_keys = globals().keys()

# note that CLI functions are set in cli.py
# import ortho with wildcard because we control everything here
# or at least the expose functions are elevated to the top level of ortho
# but you can still get other functions in submodules in the usual way
# note that the expose table also sends conf there hence the empties
# cannot do e.g. import ortho.submodule if the submodule is not below
# any submodule that needs to get the conf should also be on this list
expose = {
	'bash':['command_check','bash'],
	'bootstrap':[],
	'background':['backrun'],
	'cli':['get_targets','run_program'],
	'config':['set_config','setlist','set_list','set_dict','unset',
		'read_config','write_config','config_fold','set_hook',
		'config_hook_get'],
	'data':['check_repeated_keys','delve','delveset','catalog',
		'json_type_fixer','dictsub','dictsub_strict','dictsub_sparse',
		'unique_ordered'],
	'dev':['tracebacker','debugger'],
	'dictionary':['DotDict','MultiDict'],
	'environments':['environ','env_list','register_extension','load_extension'],
	'handler':['Handler'],
	'hooks':['hook_merge'],
	# note that you cannot have identical names for the module and a function
	'hypos':['hypothesis','sweeper'],
	'imports':['importer'],
	'unit_tester':['unit_tester'],
	'misc':['listify','unique','uniform','treeview','str_types',
		'string_types','say','ctext','confirm','status','Observer',
		'compare_dicts','Hook','mkdirs'],
	'modules':['sync'],
	'packman':['packs','github_install'],
	'ports':['check_port'],
	'reexec':['iteratively_execute','interact'],
	'requires':['requires_program','requires_python','requires_python_check',
		'is_terminal_command'],
	'timer':['time_limit','TimeoutException'],}

# note that packages which use ortho can just import the items above directly
#   however ortho submodules have to import from the correct submodule `e.g. from .misc import str_types`
#   which means that we have to update these internal imports if we later move around some of the functions

# use `python -c "import ortho"` to bootstrap the makefile
if (os.path.splitext(os.path.basename(__file__))[0]!='__init__' or not os.path.isdir('ortho')): 
	if not os.path.isdir('ortho'):
		# check site packages
		reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
		installed_packages = [r.decode().split('==')[0] for r in reqs.split()]
		if 'ortho' not in installed_packages:
			#! currently ortho must be a local module (a folder)
			raise Exception('current directory is %s and ortho folder is missing'%os.getcwd())
		else: pass
	else: raise Exception('__file__=%s'%__file__)
# makefile is bootstrapped if we have an ortho directory, hence not if using pip-installed ortho
elif not os.path.isfile('makefile'):
	import shutil
	print('bootstrapping makefile from ortho')
	shutil.copy('./ortho/makefile.bak','./makefile')
	sys.exit(0)
else: pass

def prepare_print(override=False):
	"""
	Prepare a special override print function.
	This decorator stylizes print statements so that printing a tuple that begins with words like `status` 
	will cause print to prepend `[STATUS]` to each line. This makes the output somewhat more readable but
	otherwise does not affect printing. We use builtins to distribute the function. Any python 2 code which 
	imports `print_function` from `__future__` gets the stylized print function. Any python 3 code which 
	uses print will print this correctly. The elif which uses a regex means that the overloaded print
	can turn e.g. print('debug something bad happened')	into "[DEBUG] something bad happened" in stdout.
	"""
	# python 2/3 builtins
	try: import __builtin__ as builtins
	except ImportError: import builtins
	# use custom print function everywhere
	if builtins.__dict__['print'].__name__!='print_stylized':
		# every script must import print_function from __future__ or syntax error
		# hold the standard print
		_print = print
		key_leads = ['status','warning','error','note','usage',
			'exception','except','question','run','tail','watch',
			'bash','debug']
		key_leads_regex = re.compile(r'^(?:(%s)\s)(.+)$'%'|'.join(key_leads))
		def print_stylized(*args,**kwargs):
			"""Custom print function."""
			if (len(args)>0 and 
				isinstance(args[0],str_types) and args[0] in key_leads):
				return _print('[%s]'%args[0].upper(),*args[1:])
			# regex here adds very little time and allows more natural print 
			#   statements to be capitalized
			#! note that we can retire all print('debug','message') statements
			elif len(args)==1 and isinstance(args[0],str_types):
				match = key_leads_regex.match(args[0])
				if match: return _print(
					'[%s]'%match.group(1).upper(),match.group(2),**kwargs)
				else: return _print(*args,**kwargs)
			else: return _print(*args,**kwargs)
		# export custom print function before other imports
		# this code ensures that in python 3 we overload print
		#   while any python 2 code that wishes to use overloaded print
		#   must of course from __future__ import print_function
		builtins.print = print_stylized

# special printing happens before imports
prepare_print()

# skip imports and exit if we only want the environment
import json,sys
if os.environ.get('ENV_PROBE',False):
	if not os.path.isfile('config.json'): sys.exit()
	conf = json.load(open('config.json','r'))
	env_cmd = conf.get('activate_env','')
	outgoing = 'environment: %s'%env_cmd
	ready_check = conf.get('env_ready',{})
	if env_cmd and not ready_check: print(outgoing)
	elif env_cmd and ready_check:
		for k,v in ready_check.items():
			if v!=os.environ.get(k,None): 
				print(outgoing)
	# return to makefile
	sys.exit(0)

import pprint,importlib

# import automatically
for key in expose.keys(): mod = importlib.import_module('.%s'%key,package='ortho')

# hardcoded configuration location
config_fn = 'config.json'
# hardcoded default
default_config = {}

# pylint: disable=undefined-variable
conf = config.read_config(config_fn,default=default_config)

# distribute configuration to submodules
for key in ['conf','config_fn']:
	for mod in expose: globals()[mod].__dict__[key] = globals()[key]

# expose utility functions
_ortho_keys = list(set([i for j in [v for k,v in expose.items()] for i in j]))
for mod,ups in expose.items():
	# note the utility functions for screening later
	globals()[mod].__dict__['_ortho_keys'] = _ortho_keys
	for up in ups: 
		globals()[up] = globals()[mod].__dict__[up]

# if the tee flag is set then we dump stdout and stderr to a file
tee_fn = conf.get('tee',False)
if tee_fn:
	#! we could move the log aside here
	if os.path.isfile(tee_fn): os.remove(tee_fn)
	from .bash import TeeMultiplexer
	stdout_prev = sys.stdout
	sys.stdout = TeeMultiplexer(stdout_prev,open(tee_fn,'a'))
	stderr_prev = sys.stderr
	sys.stderr = TeeMultiplexer(stdout_prev,open(tee_fn,'a'))

### LEGACY FUNCTIONS

def abspath(path): 
	"""Legacy wrapper for resolving absolute paths that may contain tilde."""
	return os.path.abspath(os.path.expanduser(path))

# clean up the namespace
retain_keys = set(['prepare_print','abspath','conf'])
added = (set(globals().keys())-set(_init_keys)
	-set([i for j in expose.values() for i in j])
	-set(expose.keys())
	-retain_keys)
for key in added: del globals()[key]
del globals()['key']
del globals()['added']
