#!/usr/bin/env python

import os,sys,subprocess,re,time,glob,shutil

__all__ = ['locate','flag_search','config','watch','layout','gromacs_config','bootstrap','notebook']

from datapack import asciitree,delve,delveset,yamlb

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
make set module source="$up/amx-charmm.git" spot="inputs/charmm"
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

def notebook(procedure,rewrite=False,go=False,name='notebook.ipynb'):
	"""
	Make an IPython notebook for a particular procedure.
	"""
	if not rewrite and os.path.isfile(name): raise Exception('refusing to overwrite %s'%name)
	if rewrite: subprocess.check_call('make clean sure',shell=True)
	#---run make prep per usual
	subprocess.check_call('make prep %s'%procedure,shell=True)
	import nbformat as nbf
	import json,pprint
	nb = nbf.v4.new_notebook()
	#---write the header
	text = "# %s\n"%procedure +\
		"\n*an AUTOMACS script*\n\n**Note:** you should only changes settings blocks before executing "+\
		"these codes in the given sequence."
	nb['cells'].append(nbf.v4.new_markdown_cell(text))
	#---always clean and prepare again
	reset = "%%capture\n! "+"make clean sure && make prep %s"%procedure
	nb['cells'].append(nbf.v4.new_code_cell(reset))
	#---! autoscrolling option causes overlaps
	autoscroll = "%%html\n"+"<style> .output_wrapper, .output {height:auto!important;max-height:100px; }"+\
		" .output_scroll {box-shadow:none!important;webkit-box-shadow:none!important;}</style>"
	#---! diabled
	if False: nb['cells'].append(nbf.v4.new_code_cell(autoscroll))
	#---note that we use inference to distinguish metarun from run
	#---! quick scripts may not work with the notebook format
	#---loop over valid experiment files
	expt_fns = sorted(glob.glob('expt*.json'))
	if not expt_fns: raise Exception('cannot find experiments')
	is_metarun = len(expt_fns)>1
	for stepno,expt_fn in enumerate(expt_fns):
		#---unpack the expt.json file into readable items
		with open(expt_fn) as fp: expt = json.loads(fp.read())
		script_fn = expt['script']
		#---settings block gets its own text
		settings = expt.pop('settings')
		settings_block = 'settings = """%s"""'%settings
		if 'settings_overrides' in expt: 
			settings_block += '\n\nsettings_overrides = """%s"""'%expt.pop('settings_overrides')
		#---warning to the user about what happens next
		if is_metarun: 
			step_name = yamlb(settings)['step']
			nb['cells'].append(nbf.v4.new_markdown_cell('# step %d: %s'%(stepno+1,step_name)))
		nb['cells'].append(nbf.v4.new_code_cell(settings_block))
		#---rewrite metadata
		rewrite_expt = "import json,shutil\nsets = dict(settings=settings)\n"+\
			"if 'settings_overrides' in globals():\n\tsets['settings_overrides'] = settings_overrides"+\
			"\n\tdel settings_overrides\n"+\
			"expt = dict(metadata,**sets)\n"+\
			"with open('expt.json','w') as fp: json.dump(expt,fp)"+\
			"\nshutil.copyfile(expt['script'],'script.py');"
		nb['cells'].append(nbf.v4.new_code_cell('#---save settings (run this cell without edits)\n'+
			'metadata = %s\n'%pprint.pformat(expt)+rewrite_expt))
		with open(script_fn) as fp: text = fp.read()
		regex_no_hashbang = '^#!/usr/bin/env python\n\s*\n(.+)\n?$'
		try: code = re.match(regex_no_hashbang,text,re.M+re.DOTALL).group(1).strip('\n')
		except: code = text
		#---time the run/step
		code = "%%time\n"+code
		#---if this step in the metarun is a standard run we write the code block
		if 'quick' in expt: nb['cells'].append(nbf.v4.new_code_cell('! python -B script.py'))
		#---standard runs are written directly to cells
		else: nb['cells'].append(nbf.v4.new_code_cell(code))
		#---add a coda if available
		#---! note that this feature requires extra routing via controlspec.py
		if 'jupyter_coda' in expt: nb['cells'].append(nbf.v4.new_code_cell(expt['jupyter_coda'].strip('\n')))

	#---write the notebook
	with open(name,'w') as f: nbf.write(nb,f)
	#---run the notebook directly with os.system so INT works
	if go: os.system('jupyter notebook %s'%name)
	else: print('[STATUS] notebook is ready at %s. '%name+
		'run this manually or use the "go" flag next time.')
