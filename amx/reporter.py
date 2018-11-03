#!/usr/bin/env python

from __future__ import print_function
import sys
import time

#! the state is automatically distributed everywhere but we have to request it here...
from amx import state

# functions which do not need to be logged
_not_logged = ['make_step','gromacs_initializer','init']

def call_reporter(func,force=True):
	"""Every function reports itself."""
	def loud(*args,**kwargs):
		if not hasattr(func,'__code__'):
			#! classes need developed
			print('status','calling non-function: %s'%str(func))
			return func(*args,**kwargs)	
		argnames = func.__code__.co_varnames[:func.__code__.co_argcount]
		noted = func.__name__+"("+','.join('%s=%r' % entry
			for entry in list(zip(argnames,args[:len(argnames)]))+
			[("args",list(args[len(argnames):]))]+
			[("kwargs",kwargs)])+")"
		# print to stdout
		print('run',noted)
		# write to a log file
		if state.step_log_file:
			with open(state['step_log_file'],'a') as fp: 
				fp.write(noted+'\n')
		else: 
			# ensure that only make_step is not written to the step file
			#   so all other functions are reported
			if func.__name__ in _not_logged:
				print('note',('the following command (%s) is not '+
					'logged to the step log')%func.__name__)
			else: 
				raise Exception(
					('note that the function %s is not logged to the step file. '
					'if this function should not be logged (i.e. it appears before '
					'a make_step call) then you should add it to the not_logged list.')%
					func.__name__)
		# accrue a history in the state
		if 'history' not in state: state.history = []
		state.history.append(noted)
		return func(*args,**kwargs)
	# rename the function
	loud.__name__ = func.__name__
	return loud
