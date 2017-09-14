#!/usr/bin/env python

"""
STATES

Functions which save the ``state`` on completion or error, along with a function (``call_reporter``) which 
logs every function call.
"""

import json,re,shutil,os
from loadstate import expt,settings
from makeface import fab

__all__ = []

def statesave(state):
	"""One stop for saving the state. Strips functions saved to `funcs` keyword."""
	calls = [key for key,val in state.items() if hasattr(val,'__call__')]
	#---check on _funcs without modifying the state
	nosaves = state.get('_funcs',[])
	#---we make sure that the only functions in the state were registered and added to _funcs
	if not set(calls)==set(nosaves): 
		#---custom exception exception (for serial_number)
		if not (set(calls)==set([]) and 
			set(nosaves)==set(['q'])):
			raise Exception('savestate finds that state._funcs is not equivalent to callables')
	try: 
		state_out = dict([(k,v) for k,v in state.items() if k not in set(nosaves+['_protect'])]) 
		text = json.dumps(state_out)
	except: raise Exception('failed to drop the json state to disk')
	with open('state.json','w') as fp: fp.write(text)

def finished(state,script_fn='script.py'):
	"""
	Save the state on completion.
	Note that this can be run more than once since statesave doesn't modify the state.
	That means that you can end your script with finished(state) so that it saves the state even if users
	perform a manual execution.
	"""
	print('[NOTE] finished and saving state.json')
	with open(script_fn) as fp: state.script_code = fp.read()
	state.status = 'completed'
	statesave(state)
	#---after saving the state we attempt to back up the state.json file for posterity
	#---...this is essential for state.before which is populated with previous states by the init function
	#---saving state_N.json here will supercede the same call at the end of the metarun function
	if not os.path.isfile('state_%d.json'%state.stepno):
		shutil.copyfile('state.json','state_%d.json'%state.stepno)

def stopper(state,exc,show_trace=True,last_lineno=None,script_fn='script.py'):
	"""
	Handle errors during execution.
	Get a DotDict with protected keywords and dump to json.
	Stopper is the complement to run, but must be outside of acme.
	"""
	#---if a state exists we perform iterative redevelopment.
	import sys,traceback
	exc_type,exc_obj,exc_tb = sys.exc_info()
	#---overwrite the error
	try:
		error = [dict(line=t.line,name=t.name,lineno=t.lineno,filename=t.filename) 
			for t in traceback.extract_tb(exc_tb)]
	except:
		#---python 2 alternate
		tb_ex_py2_order = 'filename lineno name line'.split()
		error = [dict([(j,i[jj]) for jj,j in enumerate(tb_ex_py2_order)]) 
			for ii,i in enumerate(traceback.extract_tb(exc_tb))]
	#---drop error information into the state in one dictionary
	errorpack = {'error':error,'error_exception':str(exc)}
	#---! if somebody edits script.py between start and stop then this would cause problems
	with open(script_fn) as fp: errorpack['script_code'] = fp.read()
	if last_lineno: errorpack['last_lineno'] = last_lineno
	#---all error information is in _error except the status
	state.status = 'error'
	state._error = errorpack
	#---write the traceback
	tag = fab('[TRACEBACK]','gray')
	tracetext = tag+re.sub(r'\n','\n%s '%tag,str(''.join(traceback.format_tb(exc_tb)).strip()))
	if show_trace: print(tracetext)
	print(fab('[ERROR]','red_black')+' '+fab('%s'%exc,'cyan_black'))
	statesave(state)

def call_reporter(func,state={}):
	"""Every function reports itself. Send this to __init__.py so exposed functions are loud."""
	def loud(*args,**kwargs):
		argnames = func.__code__.co_varnames[:func.__code__.co_argcount]
		noted = func.__name__+"("+','.join('%s=%r' % entry
			for entry in list(zip(argnames,args[:len(argnames)]))+
			[("args",list(args[len(argnames):]))]+
			[("kwargs",kwargs)])+")"
		#---if make_step registered a log file, we also write this to that file
		if 'step_log_file' in state:
			#---! note that `make quick vmd_protein` needs to use the state without q in many functions
			no_log_needed = ['init','make_sidestep','get_last_frame',
				'get_trajectory','gmx_run','call_reporter','get_last_gmx_call','write_continue_script']
			if 'q' not in state and func.__name__ not in no_log_needed: 
				raise Exception('dev error: %s called the reporter '%func.__name__+
					'before the "q" function was registered. if this is okay, add the function '+
					'to the no_log_needed list (%s) in acme.py '%no_log_needed)
			with open(state['step_log_file'],'a') as fp: fp.write(noted+'\n')
		else: print('[NOTE] the following command is not logged to the step log')
		print('[RUN] %s'%noted)
		if 'history' not in state: state.history = []
		state.history.append(noted)
		return func(*args,**kwargs)
	#---rename the function
	loud.__name__ = func.__name__
	return loud

def state_set_and_save(state,**kwargs):
	"""
	Some functions lack access to the global state so we 
	"""
	state.update(**kwargs)
	#---! statesave requires the state as arg. if it is not global, this will fail
	statesave(state)
