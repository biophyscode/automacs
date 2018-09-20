#!/usr/bin/env python

import os,shutil,json
from ortho.misc import listify

_shared_extensions = ['make_step','copy_file','copy_files','move_file']

def make_step(name):
	"""
	Make a new step, with folder.
	"""
	#! need to refactor state.before
	# note any previous states
	if state.before:
		# get step information from the last state
		prev_state = state.before[-1]
		if state.stepno: state.stepno += 1
		else: state.stepno = prev_state['stepno'] + 1
		state.steps = list(prev_state['steps'])
	# no previous states
	else:
		if 'stepno' not in state: state.stepno = 1
		if 'steps' not in state: state.steps = []
		else: state.stepno += 1
	# note automatic fallback to settings but returns None if no match
	step_name = state.step
	if not step_name: raise Exception('state or settings must supply a step')
	state.step = 's%02d-%s'%(state.stepno,name)
	os.mkdir(state.step)
	state.here = os.path.join(state.step,'')
	# register a log file for this step.
	# log files are in the step folder, and use the step name with ".log"
	state.step_log_file = os.path.join(state.here,state.step+'.log')
	state.steps.append(state.step)
	#! previously used make_step_hook in settings to perform additional setup tasks from extension modules
	#! ... by attaching the amx module itself to state and the hook by string from amx globals
	# note that files are not recopied on re-run because if make-step only runs once during iterative execute
	# special: copy all files
	for fn in listify(state.get('files',[])):
		if not os.path.isfile(fn): raise Exception('cannot find an item requested in files: %s'%fn)
		shutil.copyfile(fn,os.path.join(state.here,os.path.basename(fn)))
	# special: copy all sources
	for dn in state.get('sources',[]):
		if os.path.basename(dn)=='.': raise Exception('not a valid source: %s'%dn)
		if not os.path.isdir(dn): raise Exception('requested source %s is not a directory'%dn)
		shutil.copytree(dn,os.path.join(state.here,os.path.basename(dn)))
	# special: retrieve files from the file registry
	if state.before and state.file_registry:
		for fn in state.file_registry: 
			shutil.copyfile(prev_state['here']+fn,state.here+fn)

def copy_file(src,dst,**kwargs):
	"""Wrapper for copying files."""
	cwd = os.path.join(kwargs.get('cwd',state.here),'')
	shutil.copyfile(cwd+src,cwd+dst)
	
def copy_files(src,dst):
	"""Wrapper for copying files with a glob."""
	if not os.path.isdir(dst): raise Exception('destination for copy_files must be a directory: %s'%dst)
	for fn in glob.glob(src): shutil.copy(fn,dst)

def move_file(src,dest,**kwargs):
	"""Wrapper for moving files."""
	cwd = os.path.join(kwargs.get('cwd',state.here),'')
	shutil.move(cwd+src,cwd+dest)

def automacs_refresh():
	"""
	Get the experiment for amx/__init__.py.
	Note that moving this to a separate function was designed to make it easier to reload the experiment.
	However, this is better achieved by reimporting (deleting and importing) amx when necessary. This occurs
	when the go function runs the script.py directly in the same python call. See runner.execution.execute.
	"""
	_has_state = os.path.isfile('state.json')
	if _has_state: print('status','found a previous state at state.json')

	"""
	DEV NOTES!!!
	previous method moved expt_1.json to expt.json so it would be read 
		and automatically read state.json if available
	since we have no information on why automacs was imported we have to do some inference
	the run functions in execution.py should handle the exceptions so that we always have the right files here
	use ortho to direct automacs?
	needs:
	- tracebacker?
	- magic imports i.e. acme submodulator
	"""

	from .state import AMXState
	settings = AMXState(me='settings',underscores=True)
	state = AMXState(settings,me='state',upnames={0:'settings'})
	# import of the amx package depends on expt.json and any functions that do not require special importing
	#   which occurs outside of the main import e.g. amx/gromacs/configurator.py: gromacs_config
	blank_expt = {'settings':{}}
	if not os.path.isfile('expt.json'): incoming = blank_expt
	else:
		with open('expt.json') as fp: incoming = json.load(fp)
	meta = incoming.pop('meta',{})
	# the expt variable has strict attribute lookups
	expt = AMXState(me='expt',strict=True,base=incoming)
	expt.meta = AMXState(me='expt.meta',strict=True,base=meta)
	settings.update(**expt.get('settings',{}))
	if _has_state: print('dev','get the state here!')

	return dict(_has_state=_has_state,settings=settings,state=state,expt=expt)
