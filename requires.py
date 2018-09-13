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

def requires_program(*reqs):
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

def requires_python(*reqs):
	def decorator(function):
		def wrapper(*args,**kwargs):
			for req in reqs:
				try: __import__(req)
				except Exception as e:
					raise Exception(('function "%s" expects python module "%s". '
						'you may need to point to an environment by running: '
						'make set activate_env="~/path/to/bin/activate env_name"')%(function.__name__,req))
			result = function(*args,**kwargs)
			return result
		return wrapper
	return decorator
