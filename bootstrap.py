#!/usr/bin/env python

__all__ = ['bootstrap']

def bootstrap(post=True):
	"""
	This function runs setup commands from `bootstrap.py`.
	It is automatically interpreted from read_config if config.json is absent. If `config.json` is missing
	and we find bootstrap.py and it supplies a function called `bootstrap_default` then that function's 
	return value serves as the default configuration. 
	After writing the default configuration, we run `bootstrap_post()` if it is available. This function also
	runs on any repeated execution of `make bootstrap` from the command line. 
	"""
	import importlib,os,sys
	if not os.path.isfile('bootstrap.py'): return None
	# import to run the script
	if (sys.version_info < (3, 0)): mod = importlib.import_module('bootstrap',package='.')
	else: mod = importlib.import_module('bootstrap',package=None)
	has_bootstrap_default = hasattr(mod,'bootstrap_default')
	has_bootstrap_post = hasattr(mod,'bootstrap_post')
	if not has_bootstrap_post and not has_bootstrap_default:
		# this warning is invisible when ortho runs for the first time to make config.json but 
		# ... read_config will warn the user if these functions are both
		print('warning','the local bootstrap.py lacks functions bootstrap_default or boostrap_post')
	outgoing = {}
	if has_bootstrap_default: outgoing['default'] = mod.bootstrap_default()
	if has_bootstrap_post: outgoing['post'] = mod.bootstrap_post
	# when not initializing we skip the default configuration and just run the post
	#! this is somewhat arbitrary. we may wish to reconfigure on make bootstrap using the default
	if post and has_bootstrap_post: mod.bootstrap_post()
	# read_config only collects post and runs it after setting up default configuration
	return outgoing
