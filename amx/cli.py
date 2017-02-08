#!/usr/bin/env python

import os,sys,subprocess,re,time,glob,shutil

__all__ = ['locate','flag_search','config','watch','layout','gromacs_config','bootstrap']

from datapack import asciitree,delve,delveset

def locate(keyword):
	"""
	Locate the source code for a python function which is visible to the controller.

	Parameters
	----------
	keyword : string
		Any part of a function name (including regular expressions)

	Notes
	-----
	This controller script is grepped by the makefile in order to expose its python functions to the makefile
	interface so that users can run e.g. "make program protein" in orer to access the ``program`` function
	above. The ``makeface`` function routes makefile arguments and keyword arguments into python's functions.
	The makefile also detects python functions from any scripts located in amx/procedures/extras.
	The ``locate`` function is useful for finding functions which may be found in many parts of the automacs
	directory structure.
	"""
	os.system('find ./ -name "*.py" | xargs egrep --color=always "def \w*%s\w*"'%keyword)

def flag_search(keyword):
	"""
	Search the codebase for cases where a settings flag is requested.
	"""
	keyword_ambig = re.sub('( |_)','[_ ]+',keyword)
	cmd = 'egrep -nr --color=always "\.((q|get)\(\')?%s" * -R'%keyword_ambig
	print('[NOTE] running "%s"'%cmd)
	os.system(cmd)

def config():
	"""
	Print the config in a tree form using the (hidden) asciitree function above.
	"""
	config_this = {}
	with open('config.py') as fp: config_this = eval(fp.read())
	asciitree(config_this)

def watch():
	"""
	Wrapper for a command which tails the oldest mdrun command.
	"""
	#---original command works well for watching the last mdrun but doesn't monitor the files
	cmd = 'find ./ -name "log-mdrun*" | xargs ls -ltrh | '+\
		'tail -n 1 | awk \'{print $9}\' | xargs tail -f'
	os.system(cmd)

def layout(name=None):
	"""Map all teh codes."""
	#---collect python scripts
	codes = []
	for rn,dns,fns in os.walk('.'):
		codes_here = [i for i in fns if os.path.splitext(i)[-1]=='.py']
		codes.extend([os.path.join(rn,f) for f in codes_here])
	codetoc = {}
	for fn in codes:
		route = fn.split(os.sep)
		delveset(codetoc,*route,value=[])
	for fn in codes:
		with open(fn) as fp: text = fp.read()
		funcs = [j.group(1) for j in [re.match('^((?:def|class)\s*.*?)\(',t) for t in text.splitlines()] if j]
		for func in funcs:
			route = fn.split(os.sep)
			delve(codetoc,*route).append(func)
	#---sloppy
	codetoc = codetoc['.']
	if not name: asciitree(codetoc)
	else: asciitree(codetoc[name])

def gromacs_config(where=None):
	"""
	Make sure there is a gromacs configuration available.
	"""
	config_std = '~/.automacs.py'
	config_local = 'gromacs_config.py'
	#---instead of using config.py, we hard-code a global config location
	#---the global configuration is overridden if a local config file exists
	#---we source the config from a default copy in the amx directory
	default_config = 'gromacs_config.py.bak'
	if where:
		if where not in ['home','local']:
			#---! print the error message here?
			raise Exception('[ERROR] options are `make gromacs_config local` or `make gromacs_config home`. '+
				'the argument tells us whether to write a local (%s) or global (%s) configuration'%
				(config_local,config_std))
		else:
			dest_fn = config_local if where=='local' else config_std
			dest_fn_abs = os.path.abspath(os.path.expanduser(dest_fn))
			shutil.copyfile(os.path.join(os.path.dirname(__file__),default_config),dest_fn_abs)
			return dest_fn_abs
	config_std_path = os.path.abspath(os.path.expanduser(config_std))
	config_local_path = os.path.abspath(os.path.expanduser(config_local))
	has_std = os.path.isfile(config_std_path)
	has_local = os.path.isfile(config_local_path)
	if has_local: 
		print('[NOTE] using local gromacs configuration at ./gromacs_config.py')
		return config_local_path
	elif has_std: return config_std_path
	else: 
		import textwrap
		msg = ("we cannot find either a global (%s) or local (%s) "%(config_std,config_local)+
			"gromacs path configuration file. the global location (a hidden file in your home directory) "+
			"is the default, but you can override it with a local copy. "+
			"run `make gromacs_config home` or `make gromacs_config local` to write a default configuration to "+
			"either location. then you can continue to use automacs.")
		raise Exception('\n'.join(['[ERROR] %s'%i for i in textwrap.wrap(msg,width=80)]))

###---KICKSTART SCRIPTS

kickstarters = {'full':"""
make set module source="$up/amx-proteins.git" spot="amx/proteins"
make set module source="$up/amx-extras.git" spot="inputs/extras"
make set module source="$up/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="$up/amx-vmd.git" spot="inputs/vmd"
make set module source="$up/amx-bilayers.git" spot="inputs/bilayers"
make set module source="$up/amx-martini.git" spot="inputs/martini"
make set module source="$up/amx-structures.git" spot="inputs/structure-repo"
""",
'proteins':"""
make set module source="$up/amx-proteins.git" spot="amx/proteins"
make set module source="$up/amx-extras.git" spot="inputs/extras"
make set module source="$up/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="$up/amx-vmd.git" spot="inputs/vmd"
"""
}

def bootstrap(name):
	"""
	Run this after cloning a fresh copy of automacs in order to clone some standard
	"""
	#---! hard-coding the source for now, but it would be good to put this in config.py
	upstream_source = "http://github.com/bradleyrp"
	if name not in kickstarters: raise Exception('cannot find kickstarter script: %s'%name)
	with open('kickstart.sh','w') as fp:
		fp.write("#!/bin/bash\n\nset -e\n\nup=%s\n\n"%upstream_source+kickstarters[name])
	subprocess.check_call('bash kickstart.sh',shell=True)
	os.remove('kickstart.sh')
	print('[WARNING] bootstrap also runs `make gromacs_config local`\n'+
		'so you are ready to simulate. consider using `make gromacs_config home`\n'+
		'to make a machine-specific configuration for future simulations.')
	subprocess.check_call('make gromacs_config home',shell=True)
	print('[STATUS] you just pulled yourself up by your bootstraps!')
