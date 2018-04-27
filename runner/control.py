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
from datapack import str_types #! wasteful?

__all__ = ['look','quick','prep','run','metarun','clean','back',
	'preplist','set_config','go','prep_json','audit']

def fetch_script(src,cwd='./'):
	"""
	Finds the path for a parent script.
	"""
	fn = get_path_to_module(src)
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
	print('[NOTE] use `statesave(state)` or '
		'`state_set_and_save(state,**kwargs) to update the state`')
	if not os.path.isfile(state): raise Exception('cannot find %s'%state)
	bname = re.sub('\.','_',os.path.splitext(state)[0])
	if bname!='state': print('[NOTE] the state is called %s'%bname)
	#---! no tab completion in python 2 for some reason
	os.system('python -B -i -c "import json,sys;sys.path.insert(0,\'runner\');'+
		'from states import statesave,state_set_and_save;'+
		'exec(open(\'amx/pythonrc.py\').read());'+'from datapack import DotDict;'
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

def preplist(silent=False,verbose=False):
	"""
	Identify all available experiments and print them for the user.

	Note the following tagging conventions. 
		1. support means that this run/quick is called by a metarun 
			and hence should never be called by the user
		2. once means you only need to run it once because it manipulates inputs
			and conversely you probably have to expunge it manually to start over
	"""
	#---both preplist and prep are the initial user-commands so we check for install here
	is_installed()
	from makeface import fab
	from datapack import asciitree
	inputlib,spots = read_inputs(procname=None,return_paths=True)
	toc,counter = {'run':[],'metarun':[],'quick':[]},0
	#---the toc has fancy formatting for the terminal, so we make a clean version
	toc_clean = {'run':[],'metarun':[],'quick':[]}
	expt_order = []
	#---! the following notes the cwd but not the _expts.py file for a particular experiment
	dottoc = lambda counter,key,at,lead='',trail='' : (
		(fab(str(counter).rjust(4),'white_black')+' ' if counter else '')+
		lead+key+(fab(' (%s)'%at,'gray') if at else '')+trail)
	for key in sorted(inputlib.keys()):
		#---ignore comments
		if re.match('comment_',key): continue
		val = inputlib[key]
		lead = ''
		if 'tags' in val and verbose:
			#---special tags for the simulation scale
			if 'cgmd' in val['tags']: lead += fab('cgmd','cyan_black')+' '
			if 'aamd' in val['tags']: lead += fab('aamd','green_black')+' '
			if 'aamd_cgmd' in val['tags'] or 'cgmd_aamd' in val['tags']: 
				lead += fab('  md','white_black')+' '
			#---tags prefixed with "tag_" are emphasized
			tags_tag = [re.match('^tag_(.+)$',i).group(1) for i in val['tags'] if re.match('^tag_',i)]
			for tag in tags_tag: lead += fab('%s'%tag,'cyan_black')+' '
			#---dev and test notes are bright red
			if 'dev' in val['tags']: lead += fab('DEV','red_black')+' '
			if 'test' in val['tags']: lead += fab('TEST?','red_black')+' '
			#---passing test sets are marked in magenta/gray
			tags_test = [re.match('^tested_(.+)$',i).group(1) for i in val['tags'] if re.match('^tested_',i)]
			for tag in tags_test: lead += fab('+%s'%tag,'mag_gray')+' '
			#---minor notes get white on black text
			tags_notes = [re.match('^note_(.+)$',i).group(1) for i in val['tags'] if re.match('^note_',i)]
			for tag in tags_notes: lead += fab('%s'%tag,'white_black')+' '
		if 'metarun' in val: 
			toc['metarun'].append(dottoc(str(counter+1),key,spots[key],lead=lead))
		elif 'quick' in val: toc['quick'].append(dottoc(counter+1,key,spots[key],lead=lead))
		#---only three types here
		else: toc['run'].append(dottoc(counter+1,key,spots[key],lead=lead))
		#---add to the clean copy
		if 'metarun' in val: toc_clean['metarun'].append([key,spots[key]])
		elif 'quick' in val: toc_clean['quick'].append([key,spots[key]])
		else: toc_clean['run'].append([key,spots[key]])
		expt_order.append(key)
		counter += 1
	if not silent: 
		for key in ['quick','run','metarun']: asciitree({key:toc[key]})
	return {'order':expt_order,'summary':toc_clean,'details':toc}

def audit(fancy=False,since=None):
	"""
	Candidate to replace preplist. Currently used to introspect on passing test.
	"""
	# both preplist and prep are the initial user-commands so we check for install here
	import pprint,textwrap
	from makeface import fab
	from datapack import asciitree
	inputlib,spots = read_inputs(procname=None,return_paths=True)
	stock = {}
	# interpret the tests
	categories = ['cgmd','aamd','aamd_cgmd','free','protein-bilayer',
		'test','protein','bilayer','dev','lipidome','homology','flat']
	regexes = [
		('tested[dev]','^tested_(.*?)_dev$'),
		('tested','^tested_(.*?)$'),
		('tags','^tag_(.+)$'),
		('notes','^note_(.+)$')]
	regexes.extend([(i,'^(%s)$'%i) for i in categories])
	# classify tests
	for name in sorted(inputlib.keys()):
		stock[name] = {}
		# ignore comments
		if re.match('comment_',name): continue
		val = inputlib[name]
		tags = val.get('tags',[])
		for tag in list(tags):
			for key,pattern in regexes:
				this = next((item.group(1) for item in re.compile(pattern).finditer(tag)),'')
				if this:
					if key in stock[name]: stock[name][key] = [stock[name][key]]+[this]
					else: stock[name][key] = this
					tags.remove(tag)
					break
		if tags: stock[name]['also'] = tags
	if fancy: asciitree(stock)
	else: pprint.pprint(stock)
	#!? interesting
	summary = {}
	summary['never tested'] = [k for k,v in stock.items() if 'tested' not in v]
	# follow-up reports
	if since:
		import datetime as dt
		try: timestamp = dt.datetime.strptime(since,'%Y.%M.%d.%H%m')
		except ValueError: timestamp = dt.datetime.strptime(since,'%Y.%M.%d')
		else: raise Exception('failed to interpret %s'%since)
		times = [(k,v['tested']) for k,v in stock.items() if 'tested' in v]
		before_or_never = list(summary['never tested'])
		current = []
		for name,time in times:
			max_time = time if type(time) in str_types else max(time)
			#! repetitive with above
			try: this_time = dt.datetime.strptime(max_time,'%Y.%M.%d.%H%m')
			except ValueError: this_time = dt.datetime.strptime(max_time,'%Y.%M.%d')
			else: raise Exception('failed to interpret %s'%max_time)
			if this_time>timestamp: current.append(name)
			else: before_or_never.append(name)
		summary['current'] = sorted(current)
		summary['outdated'] = sorted(before_or_never)
		print(summary.keys())
	def get_style(name): 
		if 'quick' in inputlib[name]: return 'quick'
		elif 'metarun' in inputlib[name]: return 'metarun'
		else: return 'run'
	cats = dict([(cat,['%s (%s)'%(name,get_style(name)) 
		for name in stock if cat in stock[name]]) for cat in categories])
	unclassified_tags = list(set([i for j in [stock[name].get('also',[]) 
		for name in stock] for i in j]))
	if unclassified_tags: 
		raise Exception('cannot recognize all tags so add them to the function: %s'%unclassified_tags)
	summary['unclassified tags'] = list(set([i for j in [stock[name].get('also',[]) 
		for name in stock] for i in j]))
	asciitree(dict(categories=cats))
	pass_cats = ['current','never tested','outdated']
	total = len(set([i for j in [summary[k] for k in pass_cats] for i in j]))
	for key in pass_cats:
		if key in summary: 
			out = textwrap.wrap(' '.join(summary[key]),width=120)
			print('\n%s (%d/%d)\n%s\n'%(key.upper(),len(summary[key]),total,'\n'.join(out)))

def prep_json():
	"""
	Print the experiments list in JSON format. Useful for  the factory.
	"""
	expts = preplist(silent=True)
	print('NOTE: '+json.dumps(expts['summary']))

def prep_single(inputlib,scriptname='script',exptname='expt',noscript=False,overrides=None):
	"""
	Prepare a single-step program.
	"""
	_keysets('run',*inputlib.keys(),check=True)
	#! run prelude if necessary. replace with bash call?	
	if 'prelude' in inputlib:
		os.system(inputlib['prelude'])
	#---get the script name
	script_fn = os.path.join(inputlib['cwd'],inputlib['script'])
	#---if the path is not local we use the @ syntax sugar and drop the cwd
	if not os.path.isfile(script_fn): script_fn = get_path_to_module(inputlib['script'])
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
	#---crude run for the prelude which is necessary for factory testing of cgmd simulations
	#---! replace this with a bash call?
	if 'prelude' in inputlib:
		os.system(inputlib['prelude'])
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

def prep(procname=None,noscript=False,v=True):
	"""
	Prepare an experiment from inputs specified by the config.
	There are two modes: a "metarun" or a single program.
	"""
	if procname==None: 
		preplist(verbose=v)
		return
	#---use numbers from the lookup table
	if procname.isdigit(): procname = preplist(silent=True)['order'][int(procname)-1]
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
	#---we define script_fn which is used throughout the script
	executor = re.sub('#---define script_fn here','script_fn = "%s"'%script,executor)
	with open('exec.py','w') as fp: fp.write(executor)
	#---only custom set traces happen here (no automatic debugging)
	try: subprocess.check_call('PYTHON_DEBUG=no python -uB exec.py',shell=True)
	except KeyboardInterrupt: 
		print('[STATUS] received INT and exiting')
		sys.exit(1)
	except Exception as e:
		from makeface import tracebacker
		tracebacker(e)
		print('[STATUS] acme run failed during `make run`')
		sys.exit(1)
	print('[STATUS] acme run lasted %.1f minutes'%((time.time()-start_time)/60.0))
	return True

def metarun():
	"""
	Run a series of simulation steps.
	"""
	if os.path.isfile('script.py') or os.path.isfile('expt.json'):
		raise Exception('refusing to run if script.py or expt.json are present. '
			'if you wish to start from scratch, use `make go <name> clean` '
			'and this will clear the old files.')
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
		#---note that this feature is centralized in the finished function in states.py so both run and metarun
		#---...or anything executed by executor.py will save the state so later steps can look up state.before
		#---...and to prevent redundancy we only save here if the file is mussing and success
		elif os.path.isfile('state.json') and not os.path.isfile('state_%d.json'%num): 
			shutil.copyfile('state.json','state_%d.json'%num)

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

def back(command=None,cwd='.',log='log-back',go=None):
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

def go(procname,clean=False,back=False):
	"""
	Sugar for running ``make prep (name) && make run`` which also works for metaruns or quick scripts.
	"""
	if clean: cleanup(sure=True)
	runtypes = ['metarun','run','quick']
	from control import _keysets
	if procname.isdigit(): procname = preplist(silent=True)['order'][int(procname)-1]
	which_runtype = [k for k in runtypes if _keysets(k,*read_inputs()[procname].keys())]
	if len(which_runtype)>1: 
		raise Exception('found %s in multiple run categories. something has gone very wrong'%procname)
	elif len(which_runtype)==0: raise Exception('something has gone wrong. no keysets match.')
	runtype = which_runtype[0]
	if back and runtype=='quick': 
		raise Exception('cannot run `make go %s` with back because it is a quick script'%procname)
	if runtype!='quick': prep(procname)
	if not back: quick(procname) if runtype=='quick' else globals()[runtype]()
	if back: 
		cmd = 'make %s'%runtype
		print('[STATUS] running in the background via `make back command="%s"'%cmd)
		subprocess.check_call('make back command="%s"'%cmd,shell=True)
