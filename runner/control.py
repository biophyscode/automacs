#!/bin/bash

"""
CONTROL 

Specify all control flow for codes managed by ACME.

This module contains the entire command-line interface for ACME, and hence it should be found in "commands" 
setting inside config.py. It includes functions which prepare and execute the experiments. It consults
controlspec.py, which describes the rules for writing experiment files loaded by acme.py. Each experiment 
typically comes with extra paths and imports, alongside a "settings" text block. The ``_keysets`` function
validates all of the incoming experiments to make sure they have all of the required metadata.
"""

import os,sys,json,glob,shutil,time,re,subprocess
from acme import read_config,config_fn,read_inputs,write_expt,set_config,get_path_to_module
from controlspec import controlspec
from loadstate import state,expt,settings
from makeface import fab

__all__ = ['look','quick','prep','run','metarun','clean','back','preplist','set_config','go']

def fetch_script(src,cwd='./'):
	"""
	Finds the path for a parent script.
	"""
	if os.path.isfile(os.path.join(cwd,src)): return src
	else: raise Exception('cannot find requested script %s at %s'%(src,cwd))

def _keysets(run,*args,**kwargs):
	"""
	Validate an experiment type to make sure it has all of the required metadata.
	Consults the ``controlspec`` variable in ``controlspec.py`` for valid metadata keys.
	"""
	check = kwargs.pop('check',False)
	if kwargs: raise Exception('invalid kwargs: %s'%kwargs)
	for keys,name in controlspec['keysets'][run].items():
		if set(keys)==set(args): return name
	if check: raise Exception(
		'requested "%s" run type, with inalid keys (see controlspec.py): "%s"'%(run,str(args)))
	else: return False

def look(state='state.json'):
	"""
	View the current state from the commandline. Useful for debugging.
	"""
	if not os.path.isfile(state): raise Exception('cannot find %s'%state)
	bname = os.path.splitext(state)[0]
	#---! no tab completion in python 2 for some reason
	os.system('python -B -i -c "import json,sys;sys.path.insert(0,\'runner\');from datapack import DotDict;'
		'%s = DotDict(**json.load(open(\'%s\')));"'%(bname,state))

def quick(procname,**kwargs):
	"""
	Prepare and run a script embedded inside an experiment file. 
	If we supply a stepno as a keyword argument, then we assume this is a metarun, and we write the 
	appropriate experiment file and script without executing it. Otherwise exeuction happens immediately.
	"""
	#---note that stepno is indexed from one
	stepno = int(kwargs.pop('stepno',-1))
	settings = kwargs.pop('settings',None)
	settings_extras = kwargs.pop('settings_extras',{})
	if kwargs: raise Exception('invalid kwargs: %s'%kwargs)
	inputlib = read_inputs(procname)
	ins = dict(inputlib)
	ins.update(cwd_source=ins.pop('cwd'))
	#---some quick calls from metarun have their own settings
	if settings: ins['settings'] = settings
	if stepno>-1: ins['script'] = script_fn = 'script_%d.py'%stepno
	else: ins['script'] = script_fn = 'script.py'
	#---pass along extras e.g. jupyter_coda
	ins.update(**settings_extras)
	#---if extensions are not present we avoid using the state
	if stepno>-1 and 'extensions' not in inputlib: ins['stateless'] = True
	#---extensions are uppercase in order to be processed
	if 'extensions' in inputlib: ins['EXTENSIONS'] = inputlib['extensions']
	#---write the experiment no matter what 
	#---...remember expt.json is always transient so you must archive it after completed steps
	write_expt(ins,fn='expt.json' if stepno==-1 else 'expt_%d.json'%stepno)
	#---previously we executed the script internally
	#---...but writing the script and executing allows access to expt.json and the importer
	import_prependum = ''
	#---handle requested imports of standard modules 
	#---...note that imports are into the global namespace of the quick script
	if 'imports' in inputlib:
		import_prependum = [
			'import os,sys',
			'sys.path.insert(0,"%s")'%read_config()['acme'],
			'from makeface import import_remote']
		for mod in inputlib['imports']:
			#---as with importing extensions, we treat modules as either a path to a module 
			#---...or a name that can be accessed from config.py
			if re.match('^@',mod): mod_path = get_path_to_module(mod)
			else: mod_path = mod
			import_prependum += ['globals().update(**import_remote("%s"))'%mod_path]
		import_prependum = '\n'.join(import_prependum)
	#---from-disk execution is left to the user, or more likely, metarun
	print('[ACME] writing quick script %s to %s'%(procname,script_fn))
	with open(script_fn,'w') as fp: 
		if import_prependum: fp.write(import_prependum+'\n\n')
		fp.write(inputlib['quick'])
	#---assigned stepno implies that this is part of a metarun so we do not execute
	#---...if this quick script is written with a number e.g. script_3.py then we leave it to 
	#---...metarun or the user to move expt.json into place
	#---normal execution happens automatically
	if stepno==-1: os.system('python -B script.py')

def preplist(silent=False):
	"""
	Identify all available experiments and print them for the user.
	"""
	#---both preplist and prep are the initial user-commands so we check for install here
	is_installed()
	from makeface import fab
	from datapack import asciitree
	inputlib,spots = read_inputs(procname=None,return_paths=True)
	toc,counter = {'run':[],'metarun':[],'quick':[]},0
	expt_order = []
	#---! the following notes the cwd but not the _expts.py file for a particular experiment
	dottoc = lambda counter,key,at : ' '+str(counter+1).ljust(4,'.')+' '+key+fab(' (%s)'%at,'gray')
	for key in sorted(inputlib.keys()):
		val = inputlib[key]
		if 'metarun' in val: toc['metarun'].append(dottoc(counter,key,spots[key]))
		elif 'quick' in val: toc['quick'].append(dottoc(counter,key,spots[key]))
		#---only three types here
		else: toc['run'].append(dottoc(counter,key,inputlib[key]['cwd']))
		expt_order.append(key)
		counter += 1
	if not silent: asciitree({'menu':toc})
	return expt_order

def prep_single(inputlib,scriptname='script',exptname='expt',noscript=False,overrides=None):
	"""
	Prepare a single-step program.
	"""
	_keysets('run',*inputlib.keys(),check=True)
	#---get the script name
	script_fn = os.path.join(inputlib['cwd'],inputlib['script'])
	script_new_fn = '%s.py'%scriptname
	#---prepare the experiment
	ins = dict(inputlib,script=script_new_fn,script_source=script_fn)
	#---rename cwd to cwd_source
	ins.update(cwd_source=ins.pop('cwd'))
	#---pass along amx_extras so they can be imported
	ins['EXTENSIONS'] = inputlib.get('extensions',None)
	#---allow settings overrides so metarun settings overrides can use original run settings
	if overrides: ins['settings_overrides'] = overrides
	#---! consoldiate script and experiment name to just use a number. run will use this naming convention
	write_expt(ins,fn='%s.json'%exptname)
	#---copy the script file into place 
	#---if the user adds `noscript` to the make call we only get the expt 
	#---...in case the user is redeveloping the local copy of script.py for `make run`
	if not noscript: shutil.copy(fetch_script(script_fn),'./%s'%script_new_fn)

def prep_metarun(inputlib):
	"""
	Prepare a series of scripts for a "metarun".
	"""
	#---prepare each step in the metarun
	_keysets('metarun',*inputlib.keys(),check=True)
	steplist = inputlib.pop('metarun')
	for stepno,item in enumerate(steplist):
		scriptname,exptname = 'script_%d'%(stepno+1),'expt_%d'%(stepno+1)
		#---pass along extras if available
		extras = dict([(key,item[key]) for key in ['jupyter_coda'] if key in item])
		#---run a standard step verbatim
		if _keysets('metarun_steps',*item.keys())=='simple': 
			#---! need to send the step name!
			prep_single(read_inputs(item['do']),scriptname=scriptname,exptname=exptname)
		#---run a step with different settings
		elif _keysets('metarun_steps',*item.keys())=='settings': 
			ins = read_inputs(item['do'])
			#---override settings in the default experiment with those in this step of the metarun
			#---note that the metarun overrides do not have to be complete. the metarun settings
			#---...block will always be attached as settings_overrides and applied after the settings
			#---...are loaded, which means that metaruns can make changes without redundant settings text
			prep_single(ins,scriptname=scriptname,exptname=exptname,overrides=item['settings'])
		#---quick to script with settings
		elif _keysets('metarun_steps',*item.keys())=='quick': 
			quick(item['quick'],settings=item['settings'],stepno=stepno+1,settings_extras=extras)
		#---run a quick script, but only write the script without entire settings replace
		elif _keysets('quick',*item.keys())=='quick': 
			quick(item['quick'],stepno=stepno+1,settings_extras=extras)
		#---write the quick script with no additional settings
		#---! elif _keysets('quick',*item.keys())=='simple': quick(item['quick'],stepno=stepno+1)
		else: raise Exception('no formula for metarun item: %r'%item)

def prep(procname=None,noscript=False):
	"""
	Prepare an experiment from inputs specified by the config.
	There are two modes: a "metarun" or a single program.
	"""
	if procname==None: 
		preplist()
		return
	#---use numbers from the lookup table
	if procname.isdigit(): procname = preplist(silent=True)[int(procname)-1]
	inputlib = read_inputs(procname)
	regular_prep_keys = 'tags script params extensions settings cwd'.split()
	quick_keys = [['settings','quick'],['settings','quick','params','extensions','tags']]
	#---! the above keys are repeated so consolidate them
	if _keysets('metarun',*inputlib.keys()): 
		if noscript: raise Exception('noscript cannot be used with metarun')
		prep_metarun(inputlib)
	elif _keysets('run',*inputlib.keys())=='std': 
		prep_single(inputlib,noscript=False)
	elif _keysets('quick',*inputlib.keys()): 
		raise Exception('this experiment is a "quick" type. use `make quick %s` instead'%procname)
	else: 
		raise Exception('invalid input keys "%s" see controlspec["keysets"]'%str(inputlib.keys()))
	
def run(procname=None,over='expt.json',script='script.py',PYTHON_DEBUG=None,look=False):
	"""
	Run a prepared acme script read from the experiment settings.
	Note that all scripts look for expt.json. 
	So if you want to run things manually, just copy your experiments, and run their script.
	But the expts have the script name so we could write a wrapper that finds the right script from an expt.
	But this function does that and even more, so it's pretty useful.
	"""
	start_time = time.time()
	if procname: prep(procname)
	msg_no_expt = 'either you want `make metarun` or expt.json is not ready'
	if not os.path.isfile(over): raise Exception('run requires %s. '%over+msg_no_expt)
	expt_in = json.load(open(over))
	if 'script' not in expt_in: raise Exception('make run cannot find "script" in %s'%over)
	script = expt_in['script']
	if not os.path.isfile(script): raise Exception('cannot find script %s requested by %s'%(script,over))
	#---if this script is a simple type, we run it directly and return without using the executor
	if expt_in.get('stateless',False):
		subprocess.check_call('PYTHON_DEBUG=no python -uB %s'%script,shell=True)
		return True
	#---create the executor script
	with open(os.path.join(os.path.dirname(__file__),'executor.py')) as fp: executor_script = fp.read()
	executor = str(executor_script)
	config = read_config()
	executor = re.sub('PATH_TO_RUNNER',config['acme'],executor_script)
	executor = re.sub('codeprep\(\)','codeprep(script_fn="%s")'%script,executor,flags=re.M)
	executor = re.sub('finished\(state\)','finished(state,script_fn="%s")'%script,executor,flags=re.M)
	executor = re.sub('stopper\(this_state,e,','stopper(this_state,e,script_fn="%s",'%
		script,executor,flags=re.M)
	with open('exec.py','w') as fp: fp.write(executor)
	#---only custom set traces happen here (no automatic debugging)
	try: subprocess.check_call('PYTHON_DEBUG=no python -uB exec.py',shell=True)
	except KeyboardInterrupt: 
		print('[STATUS] received INT and exiting')
		sys.exit(1)
		#---! previously returned False to the metarun but this doesn't allow the code to throw an error
		#return False
	#---PROPER TRACEBACK HERE???
	except Exception as e:
		from makeface import tracebacker
		tracebacker(e)
		print('[STATUS] acme run failed during `make run`')
		sys.exit(1)
		#---! previously returned False to the metarun but this doesn't allow the code to throw an error
		#return False
	print('[STATUS] acme run lasted %.1f minutes'%((time.time()-start_time)/60.0))
	return True

def metarun():
	"""
	Run a series of simulation steps.
	"""
	if os.path.isfile('script.py') or os.path.isfile('expt.json'):
		raise Exception('refusing to run if script.py or expt.json are present. this is a metarun!')
	script_fns = glob.glob('script_*.py')
	expt_fns = glob.glob('expt_*.json')
	ranges = [sorted([int(re.match('^script_(\d)+\.py$',i).group(1)) for i in script_fns]),
		sorted([int(re.match('^expt_(\d)+\.json$',i).group(1)) for i in expt_fns]),
		list(range(1,len(expt_fns)+1))]
	if not [ranges[0]==j for j in ranges[1:]]: raise Exception('problem with script/expt names')
	elif len(expt_fns)!=len(script_fns): raise Exception('different number of script and expt files')
	for num in ranges[0]:
		#---expt needs to be global and it is imported at the end of acme.py so we place it
		shutil.copyfile('expt_%d.json'%num,'expt.json')
		print(fab('[ACME] starting metarun step %d'%num,'white_black'))
		success = run(over='expt_%d.json'%num,script='script_%d.py')
		#---previously we handled the exception with a simple not and just exited for some reason
		#except Exception as e: 
		#	print('[ERROR] `make run` threw an exception')
		#	sys.exit(1)
		#---! loop continues on error for some reason
		if not success: 
			print('[ERROR] `make run` returned an error state')
			sys.exit(1)
		#---save the state for posterity, later lookups (no save if quick script doesn't save a state.json)
		elif os.path.isfile('state.json'): shutil.copyfile('state.json','state_%d.json'%num)

def cleanup(sure=False):
	"""
	Clean files from the current directory.
	"""
	config = read_config()
	if 'cleanup' not in config: raise Exception('configuration is missing cleanup instructions')
	fns = []
	for pat in config['cleanup']: fns.extend(glob.glob(pat))
	if sure or all(re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('[QUESTION] %s (y/N)? '%msg))!=None for msg in ['okay to remove','confirm']):
		for fn in fns: 
			if os.path.isfile(fn): os.remove(fn)
			else: shutil.rmtree(fn)

def clean(sure=False): cleanup(sure=sure)

def back(command=None,cwd='.',log='log-back'):
	"""
	Run a command in the background and generate a kill switch.

	Parameters
	----------
	command : string
		A terminal command used to execute the script in the background e.g. ``./script-protein.py``. You
		can also use other targets in the command e.g. ``make back command="make metarun <name>"``.
	"""
	cmd = "nohup %s > %s 2>&1 &"%(command,log)
	print('[STATUS] running the background via "%s"'%cmd)
	job = subprocess.Popen(cmd,shell=True,cwd=cwd,preexec_fn=os.setsid)
	ask = subprocess.Popen('ps xao pid,ppid,pgid,sid,comm',
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	com = ask.communicate()
	if sys.version_info>=(3,0): ret = '\n'.join([j.decode() for j in com])
	else: ret = '\n'.join(com)
	if sys.version_info>=(3,0):
		pgid = next(int(i.split()[2]) for i in ret.splitlines() if re.match('^\s*%d\s'%job.pid,i))
	else: pgid = next(int(i.split()[2]) for i in ret.splitlines() if re.match('^\s*%d\s'%job.pid,i))
	kill_script = 'script-stop-job.sh'
	term_command = 'pkill -TERM -g %d'%pgid
	with open(kill_script,'w') as fp: fp.write(term_command+'\n')
	os.chmod(kill_script,0o744)
	print('[STATUS] if you want to terminate the job, run "%s" or "./%s"'%(term_command,kill_script))
	job.communicate()

def is_installed():
	"""
	Check if installation criterion are met.
	If the config.py contains an install_check string, it is run as a command.
	The simplest way to handle installation is to have the install check command use the make interface
	to call a command available from the commands list.
	"""
	config = read_config()
	if 'install_check' in config: 
		try: subprocess.check_call(config['install_check'],shell=True)
		except: sys.exit(1)

def go(procname,clean=False):
	"""
	Sugar for running ``make prep (name) && make run`` which also works for metaruns or quick scripts.
	"""
	if clean: cleanup(sure=True)
	runtypes = ['metarun','run','quick']
	from control import _keysets
	if procname.isdigit(): procname = preplist(silent=True)[int(procname)-1]
	which_runtype = [k for k in runtypes if _keysets(k,*read_inputs()[procname].keys())]
	if len(which_runtype)>1: 
		raise Exception('found %s in multiple run categories. something has gone very wrong'%procname)
	runtype = which_runtype[0]
	if runtype!='quick':prep(procname)
	quick(procname) if runtype=='quick' else globals()[runtype]()
