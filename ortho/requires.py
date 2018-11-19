#!/usr/bin/env python

import subprocess,re

def is_terminal_command(name):
	"""
	Check returncode on which.
	"""
	check_which = subprocess.Popen('which %s'%name,shell=True,executable='/bin/bash',
		stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	check_which.communicate()
	return check_which.returncode

def version_number_compare(v1,v2):
	# via https://stackoverflow.com/questions/1714027
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
    # cmp is gone in python 3
    cmp = lambda a,b: (a > b) - (a < b)
    return cmp(normalize(v1),normalize(v2))

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

def _requires_python_check(req,msg):
	regex_version = '^(.*?)(=|>=|>)(.*?)$'
	op,version = None,0
	if re.match(regex_version,req):
		req,op,version = re.match(regex_version,req).groups()
	try: 
		mod = __import__(req)
	except Exception as e: raise Exception(msg%(req,''))
	if op:
		version_this = mod.__version__
		if (
			(op=='=' and not version_number_compare(version_this,version)==0) or
			(op=='>' and not version_number_compare(version_this,version)>0) or
			(op=='>=' and not version_number_compare(version_this,version)>=0)
			):
			raise Exception(msg%(req,
				' (requested version %s%s but found %s)'%(
					op,version,version_this)))

def requires_python_check(*reqs):
	msg = ('we expect python module "%s"%s. '
		'you may need to point to an environment by running: '
		'make set activate_env="~/path/to/bin/activate env_name"')
	for req in reqs: _requires_python_check(req,msg)

def requires_python(*reqs):
	def decorator(function):
		msg = ('function "%s"'%function.__name__+' expects python module "%s"%s. '
			'you may need to point to an environment by running: '
			'make set activate_env="~/path/to/bin/activate env_name"')
		def wrapper(*args,**kwargs):
			for req in reqs: _requires_python_check(req,msg)
			result = function(*args,**kwargs)
			return result
		return wrapper
	return decorator
