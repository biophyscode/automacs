#!/usr/bin/env python

#! try leaving out os and see what happens. impossible to debug!
#!   used: `python -c "import ortho;ortho.get_targets(verbose=True);import amx;amx.cli.gromacs_config()"`
#!   note also that it won't appear on make but it will appear from get_targets, suggesting import failure?
#!   this is really only a problem when rapidly moving code into place. best to skeleton it out first

import os,shutil

def gromacs_config(where=None):
	"""
	Make sure there is a gromacs configuration available.
	"""
	# locations for gromacs config
	# note that we avoid use of ortho because we want users to be able to easily edit the config
	config_std = '~/.automacs.py'
	config_local = 'gromacs_config.py'
	# location for the default configuration
	default_config = 'gromacs_config.py.bak'
	if where:
		if where not in ['home','local']:
			raise Exception('options are `make gromacs_config local` or `make gromacs_config home`. '+
				'the argument tells us whether to write a local (%s) or global (%s) configuration'%
				(config_local,config_std))
		else:
			dest_fn = config_local if where=='local' else config_std
			dest_fn_abs = os.path.abspath(os.path.expanduser(dest_fn))
			shutil.copyfile(os.path.join(os.path.dirname(__file__),default_config),dest_fn_abs)
			return dest_fn_abs
	config_std_path = os.path.abspath(os.path.expanduser(config_std))
	config_local_path = os.path.abspath(os.path.expanduser(config_local))
	has_std = os.path.isfile(config_std_path)
	has_local = os.path.isfile(config_local_path)
	if has_local: 
		print('note','using local gromacs configuration at ./gromacs_config.py')
		return config_local_path
	elif has_std: 
		print('note','using global gromacs configuration at ~/.automacs.py')
		return config_std_path
	else: 
		import textwrap
		msg = ("we cannot find either a global (%s) or local (%s) "%(config_std,config_local)+
			"gromacs path configuration file. the global location (a hidden file in your home directory) "+
			"is the default, but you can override it with a local copy. "+
			"run `make gromacs_config home` or `make gromacs_config local` to write a default "+
			"configuration to either location. then you can continue to use automacs.")
		raise Exception('\n'.join(['%s'%i for i in textwrap.wrap(msg,width=80)]))
