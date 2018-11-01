#!/usr/bin/env python

from __future__ import print_function
import sys

# functions which do not need to be logged
_not_logged = ['make_step','gromacs_initializer','init']

import amx
from amx import state

"""
import the state above. note that we must also export it from amx/__init__.py
for mysterious reasons. if we do not, the state that ends up here is a blank
one, and is different than the "real" state set in the global namespace of 
amx/__init__.py by output from the automacs_refresh function. we suspect this
is due to circular imports during the sequence of amx/__init__.py but at present
this problem cannot be avoided, and we wish to retain the following features:
(1) the reporter imports the state in the usual way above (2) the state is 
current (i.e. identical) with the same state which is automatically distributed 
via the magic_importer to all other modules (3) no imports inside the function
below (4) too lazy to troubleshoot the true sequence of amx/__init__.py since
the state is otherwise imported correctly, and conveniently distributed to
other modules. in short: this single import (of state) is unorthodox, but
we get a beneficial import scheme. it can be retired if we find the true 
solution to the problem of avoiding the stale state variable. note that we 
enforce all reported functions to have a step log below. this check will
catch the error, if you wish to try to fix this problem
"""

import time

#! minor bug: somewhere in the amx loop the functions are reported twice
#!   and the temporary fix here is to prevent multiple trips through the
#!   call reporter decorator below so the log file has no repeats
#!   note that this is worth fixing in the future
call_reporter_history = []

def call_reporter(func):
	"""Every function reports itself."""
	# prevent multiple call_reporter
	if func.__name__ in call_reporter_history: return func
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
	call_reporter_history.append(func.__name__)
	# rename the function
	loud.__name__ = func.__name__
	return loud
