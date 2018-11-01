#!/usr/bin/env python

from __future__ import print_function
import os,shutil,json,sys
from ortho.misc import listify

_shared_extensions = ['make_step','copy_file','copy_files','move_file']

def make_step(name):
	"""
	Make a new step, with folder.
	"""
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
	#! make the state.json name more flexible
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

	from .amxstate import AMXState
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

	# load a previous state
	if _has_state: 
		print('status','loading preexisting state')
		with open('state.json') as fp:
			raw = json.loads(fp.read())
		# merging upstream dictionaries here
		# note that we do not merge upstream dictionaries and instead replace _up and _upnames
		for k in ['_up','_upnames']: 
			if k in raw: setattr(state,k,raw.pop(k))
		state.update(**raw)
	return dict(_has_state=_has_state,settings=settings,state=state,expt=expt)

def automacs_execution_handler(namespace):

	"""
	Handle standard or supervised execution from amx/__init__.py with that namespace.
	"""

	# SUPERVISED EXECUTION is only possible with "python script.py"
	if (len(sys.argv)==1 and 
		os.path.isfile(sys.argv[0]) and
		os.path.isdir('amx')):

		# we are executing e.g. `python script.py` from the automacs root
		print('status','supervised execution starts')

		# prepare code
		script_fn = sys.argv[0]
		with open(script_fn) as fp: script_code = fp.read()
		#! for some reason we get an error on ast.parse unless this comes from amx/__init__.py
		ast = namespace['ast']
		code = ast.parse(script_code)

		# detect failure state and resume
		last_completed_lineno = -1
		if state.error_state:
			from ortho import ctext
			print('status',ctext('found failure mode for %s'%script_fn,'angry'))
			# use abstract syntax trees to avoid repeating already-completed lines
			cmd_old = [i for i in ast.iter_child_nodes(ast.parse(state.error_state['script_code']))]
			cmd_new = [i for i in ast.iter_child_nodes(ast.parse(script_code))]
			# get the first different child of root
			diffs = [ii for ii,i in enumerate(cmd_new) if ii<len(cmd_old) 
				and ast.dump(cmd_old[ii])!=ast.dump(i)]
			if len(diffs)==0:
				print('status','script %s has not changed since failure'%script_fn)
				if 'last_lineno' not in state.error_state: 
					raise Exception('identical reexecution but cannot find last_lineno')
				# if the old and new script are identical we use the recorded last_lineno to find the 
				#   last successfully executed line and then start on the *next* one
				canon_linenos = [i.lineno for i in cmd_old]
				# the first difference is the next like after the last lineno that was completed before
				if state.error_state['last_lineno'] not in canon_linenos:
					raise Exception('development. lost the right line number so we should ask the user')
				first_diff = canon_linenos.index(state.error_state['last_lineno'])+1
				last_completed_lineno = state.error_state['last_lineno']
			else: first_diff = diffs[0]
			# keep the imports
			import_inds = [ii for ii,i in enumerate(cmd_new) if type(i).__name__=='ImportFrom']
			# remove the already-completed lines unless they were imports
			remove_linenos = [code.body[i].lineno for i in set(range(first_diff))-set(import_inds)]
			print('status','resuming execution from source code lineno %d'%code.body[first_diff].lineno)
			try: print('status','resuming on function %s'%code.body[first_diff].value.func.id)
			except: pass
			# use the NodeTransformer to remove linenos below the first different line except the imports
			class CodeSurgery(ast.NodeTransformer):
				def visit(self, node):
					if hasattr(node,'lineno') and node.lineno in remove_linenos: 
						"""
						We augment the code in two ways during iterative reexecution. First, in the new_body
						section below, we add a ``last_lineno = N`` line after each completed line. The ``N`` 
						is set to the value of that line number in the tree. This line number is dumped to 
						the error state. When we reexecute, we retain the import statements. This means that
						adding an error to an imported package will absolutely break the execution because we
						assume that completed lines without imports never need to be run again, and that 
						imports always work. On reexecution, we add placeholders to completed lines here in
						the transformer. These placeholders both set last_lineno to the last completed line
						and they also have line numbers that equal this last line. This is a somewhat clumsy
						way of ensuring that even if we execute many times on a single failed line, that the
						code always remembers the last truly completed line.
						"""
						node.lineno = last_completed_lineno
						item = ast.parse('last_lineno = %d'%node.lineno).body[0]
						item.lineno = last_completed_lineno
						return item
					else: return ast.NodeTransformer.generic_visit(self, node)
			code_ready = ast.fix_missing_locations(CodeSurgery().visit(code))
			# clean up the previous error
			del state['error_state']

		# no error so we run the code as written
		else: code_ready = code

		# after each successful root's child execution we update the last_lineno
		#new_body = [[k,ast.parse('last_lineno = %d'%k.lineno).body[0]] for k in code_ready.body]
		placeholders = [ast.parse('last_lineno = %d'%k.lineno).body[0] for k in code_ready.body]
		for pp,p in enumerate(placeholders): placeholders[pp].lineno = code_ready.body[pp].lineno
		new_body = [i for j in zip(code_ready.body,placeholders) for i in j]
		code_ready = ast.fix_missing_locations(ast.Module(body=new_body))

		from ortho.dev import tracebacker
		namespace['last_lineno'] = -1
		try: exec(compile(code_ready,filename='<ast>',mode='exec'),namespace,namespace)
		except (KeyboardInterrupt,Exception) as e: 
			if isinstance(e,KeyboardInterrupt):
				print()
				print('status','caught KeyboardInterrupt')
			else: tracebacker(e)
			from ortho.misc import say
			print(say('[DEBUG]','mag_gray')+' supervisor is dumping the last line for a restart')
			# add error information to the state
			state['error_state'] = {'last_lineno':namespace['last_lineno'],'script_code':script_code}
			state._dump('state.json',overwrite=True)
			print('note','when you reexecute the script (%s) you will have the option to resume'%script_fn)
		else:
			# on success we dump the state for posterity
			#! how to name the states?
			# note that state.json will have the previous error state if we are reexecuting
			if last_completed_lineno!=-1:
				state['note_checkpoint'] = {
					'recovered':True,
					'previous_last_completed_line':last_completed_lineno,
					'script_code':script_code}
			# note that state.json will persist for reading by the next step
			#   while state_1.json will serve as a checkpoint
			#!!! DEVELOPMENT: need a hook for state names! need to recover metarun!
			state._dump('state_1.json',overwrite=True)

		# we have executed the script above so now we exit
		print('status','done')
		sys.exit(0)

	# standard execution
	else:

		def amx_excepthook_wrapped(type,value,tb):
			"""Dump the state and debug on exception."""
			#global state
			from ortho.dev import debugger
			# this function must appear in amx/__init__.py to access the state
			#! how to name the states?
			state._dump('state.json',overwrite=True)
			# debugger will be interactive if we have a terminal
			return debugger(type,value,tb)

		# non-supervised execution uses the standard debugger with state dump
		sys.excepthook = amx_excepthook_wrapped

	# note that non-supervised execution continues here, at the end of amx/__init__.py
	#   while supervised execution exits above
	return
