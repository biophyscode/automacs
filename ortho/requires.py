#!/usr/bin/env python

import subprocess

def is_terminal_command(name):
	"""
	Check returncode on which.
	"""
	check_which = subprocess.Popen('which %s'%name,shell=True,executable='/bin/bash',
		stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	check_which.communicate()
	return check_which.returncode

def requires(*reqs):
	def decorator(function):
		def wrapper(*args,**kwargs):
			for req in reqs:
				return_value = is_terminal_command(req)
				if return_value!=0: 
					raise Exception(('function %s requested a terminal command but we '
						'cannot find %s at the terminal (via `which %s`). '
						'are you sure you are in the right environment?')%(function,req,req))
			result = function(*args,**kwargs)
			return result
		return wrapper
	return decorator
