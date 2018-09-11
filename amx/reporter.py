#!/usr/bin/env python

from __future__ import print_function

def call_reporter(func,state):
	"""Every function reports itself."""
	def loud(*args,**kwargs):
		argnames = func.__code__.co_varnames[:func.__code__.co_argcount]
		noted = func.__name__+"("+','.join('%s=%r' % entry
			for entry in list(zip(argnames,args[:len(argnames)]))+
			[("args",list(args[len(argnames):]))]+
			[("kwargs",kwargs)])+")"
		# print to stdout
		print('run',noted)
		# write to a log file
		if state.step_log_file:
			with open(state['step_log_file'],'a') as fp: fp.write(noted+'\n')
		else: 
			print('note',('the following command (%s) is not '+
				'logged to the step log')%func.__name__)
		# accrue a history in the state
		if 'history' not in state: state.history = []
		state.history.append(noted)
		return func(*args,**kwargs)
	# rename the function
	loud.__name__ = func.__name__
	return loud
