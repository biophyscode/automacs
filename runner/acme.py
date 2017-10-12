#!/usr/bin/env python

"""
ACME EXPERIMENTS
----------------

Codes in this module manage reading and writing experiments. Experiments for acme-inflected simulation runs 
are written to special data structures found in python scripts containing dictionary literals. The files are 
located by :any:`get_input_files <acme.get_input_files>`.

**Note!** Your experiment files may use paths that depend on your specific configuration. You can manage these 
paths in two ways. You can either decide on a configuration (described largely by the modules list in 
config.py) and then if you decide to move something, perform batch replacements on your paths inside of the
experiment files. A more advanced option is to label paths in other modules with the "@module" syntactic 
sugar. If "module" is the directory name for a module, then @module/path/to/file will be replaced with the 
correct path, regardless of where the module is. This is handled in loadstate.py, which is the only place 
where experiments are unpacked.
"""

#---hardcoded config
config_fn = 'config.py'

import os,re,json,subprocess
import ast

from makeface import abspath
from datapack import check_repeated_keys,DotDict,yamlb,delveset,delve
from controlspec import controlspec,controlmsg

__all__ = []

def read_config(source=None):
	"""
	Read the configuration from a single dictionary literal in config.py (or the config_fn).
	"""
	source = config_fn if not source else source
	if not os.path.isfile(abspath(source)): raise Exception('cannot find file "%s"'%source)
	try: return eval(open(abspath(source)).read())
	except: raise Exception('[ERROR] failed to read master config from "%s"'%source)

def get_input_files():
	"""
	Search for experiment files in this subtree. 
	Instructions for finding these files can be found in the "inputs" key in config.py. This key can be (1) a
	single file, (2) a glob for many files, (3) a list of files or globs, or (4) a regex pattern written into
	extractable from the string if it matches ``^@regex(.+)``. The last option is the most flexible and allows
	users to find all files named ``anything_expt.py``, for example.
	"""
	config = read_config()
	#---read all of the dictionaries in the scripts pointed to by inputs into a single space
	#---the inputs argument can be a string with a glob, a list of globs, or a special regex
	if type(config['inputs'])==str and re.match('^@',config['inputs']):
		regex_rule = re.match('^@regex(.+)',config['inputs']).group(1)
		input_sources = []
		for root_dn,dns,fns in os.walk('./'):
			input_sources.extend([os.path.join(root_dn,fn) for fn in fns if re.match(regex_rule,fn)])
	else: input_sources = str_or_list(config['inputs'])
	return input_sources

def read_inputs(procname=None,return_paths=False):
	"""
	Parse all experiment files specified by ``get_input_files`` and either return the whole list or isolate
	a single procedure specified by the argument.
	"""
	inputlib = {}
	input_sources = get_input_files()
	spots = {}
	for fn in input_sources:
		with open(fn) as fp: text_spec = fp.read()
		if not check_repeated_keys(text_spec):
			raise Exception(controlmsg['json']+' error is located in: %s'%fn)
		inputlib_ins = eval(text_spec)
		#---attach location to each incoming hash
		for key,val in inputlib_ins.items():
			if 'cwd' in val: raise Exception('file %s has key %s with cwd already defined'%(fn,key))
			val['cwd'] = os.path.dirname(fn)
			#---populate the master inputlib
			#---sequential overwriting happens here
			if not procname and key in inputlib:
				raise Exception('input file %s contains a key "%s" that we already found!'%(fn,key))
			else: inputlib[key] = val
			spots[key] = fn
	if procname and return_paths: raise Exception('cannot return paths if you asked for a procedure')
	if not procname: return inputlib if not return_paths else (inputlib,spots)
	elif procname not in inputlib: raise Exception('cannot find procedure %s in the inputs'%procname)
	else: return inputlib[procname]

def write_config(config):
	"""
	Write the configuration.
	"""
	import pprint
	#---write the config
	with open(config_fn,'w') as fp: 
		fp.write('#!/usr/bin/env python -B\n'+str(pprint.pformat(config,width=110)))

def add_config(*args,**kwargs):
	"""
	Add something to the configuration dictionary located in config_fn (typically config.py).
	The path through the nested config dictionary is specified by *args.
	The many flag ensures that we add items to a non-redundant list.
	The hashed flag makes sure that we add items to a dictionary (this allows for overwriting).
	"""
	value = kwargs.pop('value',None)
	many = kwargs.pop('many',False)
	hashed = kwargs.pop('hashed',False)
	if many and hashed: raise Exception('can only use `many` or `hashed` options to add_config separately')
	if kwargs: raise Exception('unprocessed kwargs %s'%str(kwargs))
	config = read_config()
	if not hashed and not value: raise Exception('specify configuration value')
	setting_change = False
	if not hashed:
		try: exists = delve(config,*args)
		except: exists,setting_change = None,True
	if not many and not hashed:
		if exists == value: return False
		else: setting_change = True
	elif many:
		if not exists: exists = []
		elif type(exists)!=list:
			raise Exception('requested many but the return value is not a list: "%s"'%str(exists))
		#---disallow any redundancy even in a preexisting list
		if len(list(set(exists)))!=len(exists): 
			raise Exception('redundancy in settings list %s'%str(exists))
		if value not in set(exists): 
			exists.append(value)
			setting_change = True
			value = exists
		else: return False
	elif hashed:
		hash_name = args[0]
		if hash_name not in config: config[hash_name] = {}
		for arg in args[1:]:
			#---manually process equals sign since makeface cannot do 
			if '=' not in arg: raise Exception(
				'received argument to add_config with hashed=True but no equals sign: "%s"'%arg)
			key,val = arg.split('=')
			config[hash_name][key] = val
	#---set via delve as long as we are not setting a hash
	if not hashed: delveset(config,*args,value=value)
	write_config(config)
	return setting_change

def write_expt(data,fn):
	"""
	Create a new experiment file.
	Development note: this would be a good place to prevent overwriting experiment, backing it up, etc.
	"""
	with open(fn,'w') as fp: fp.write(json.dumps(data))
	#---! note that we removed an update function which loads data into global expt and global settings

def connect(source,spot):
	"""
	Clone a shared code package from a git repository and place it somewhere in the codes.
	"""
	if bool(source)^bool(spot): raise Exception('connect requires spot and source')
	if not add_config('modules',value=(source,spot),many=True): 
		raise Exception('[NOTE] already connected to that module. Remove it manually and re-add it if you want.')
	else:
		config = read_config()
		mods = config.get('modules',[])
		if not source: print('[NOTE] modules are: %s'%str(mods))
		else:
			#---clone the module
			source = source.replace('http','https')
			cmd = 'git clone %s %s'%(source,spot)
			print('[NOTE] cloning via: "%s"'%cmd)
			subprocess.check_call('git clone %s %s'%(source,spot),shell=True)
			return

def set_config(what,*args,**kwargs):
	"""
	Command-line interface to update configuration in config_fn (typically config.py). 
	This function routes ``make set ...` requests to functions here in the acme.py module, which manages all 
	experiments. Since ``set`` is a python type, we make use of the config.py alias scheme to map this 
	function to ``make set ...``.
	"""
	#---currently we can modify the following components of the config file.
	settables = 'module inputs commands links'.split()
	if what not in settables: raise Exception('make set target must be in %r'%settables)
	elif what=='module': connect(*args,**kwargs)
	elif what=='inputs': 
		if kwargs!={}: raise Exception('no kwargs allowed but received %s'%str(kwargs))
		if len(args)!=1: 
			raise Exception(
				'only one argument to `make set inputs` is allowed but received %s'%str(args))
		add_config('inputs',value=args[0],many=True)
	elif what=='commands': 
		if kwargs!={}: raise Exception('no kwargs allowed but received %s'%str(kwargs))
		for arg in args: add_config('commands',value=arg,many=True)
	elif what=='links':
		for arg in args: add_config('links',*args,hashed=True)

def get_path_to_module(code,tail=True):
	"""
	Handles the "@" syntax sugar for locating paths in other modules.
	This function is used exclusively in loadstate.py to decorate ``yamlb`` when parsing the settings
	blocks inside of experiments, which settings blocks are the only place the sugar applies.
	Given a string with "@" syntax sugar, we get a path to a module sourced by the config_fn.
	This function returns the code immediately if it is not prepended by "@", hence it is suitable for parsing
	*all* paths if you want.
	"""
	if not re.match('^@(.+)',code): return code
	parts = re.match('^@(.+)',code).group(1).split(os.sep)
	name,tail_path = parts[0],os.sep.join(parts[1:]) if len(parts)>1 else ''
	if not tail and tail_path: raise Exception(
		'[ERROR] module path %s has a tail but the calling function forbids it'%code)
	#---load the configuration
	config = read_config()
	#---get basenames from the modules
	basenames = dict([(os.path.basename(i[1]),i[1]) for i in config['modules']])
	#---make sure there are no redundant basenames: this is a design constraint!
	if len(basenames.keys())>len(set(basenames.keys())):
		raise Exception('[ERROR] detected repeated directory names in the modules list in the config')
	#---the special "@name" syntax may be followed by a path, but we look for the module first
	if name not in basenames.keys():
		#---check links here. these are an alternative path lookup
		#---! improved documentation
		if name in config.get('links',[]): lookup = config['links'][name]
		else: raise Exception('[ERROR] cannot find %s in the list of base module names or links in the config: %s'%(
			name,basenames.keys()))
	else: lookup = basenames[name]
	if tail_path: return os.path.join(lookup,tail_path)
	else: return lookup
