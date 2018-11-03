#!/usr/bin/env python

def check_installed(**kwargs):
	"""Hook for checking that gromacs is installed."""
	#! to get a function from ortho we have to specify the submodule and 
	#!   also import ortho first. this is a weird quirk of the import scheme
	# note that this is called by the gromacs_initializer which is set in
	#   the gromacs framework inside the amx config. this runs automatically
	#   whenever amx is imported, hence almost every make command. we allow
	#   users to skip the GROMACS executable check, but note that another 
	#   alternative is to expect users to run an init function at the top of
	#   the real scripts that use GROMACS. we are skipping that for now. note
	#   that adding other modules besides GROMACS might make this more 
	#   important, in which case the best option is to have the user specify
	#   some kind of with-frameworks=other_module flag which would skip
	#   the import of gromacs. I think this is better than asking users to 
	#   do further setup (i.e. call init()) besides importing amx, which is 
	#   the obvious place to initialize gromacs
	import ortho
	from ortho.requires import is_terminal_command
	msg = (" To set the GROMACS executable directly, run "
		"`make set gmx_call=\"gmx_command\"`, where the quoted string "
		"is the correct executable.")
	targets = ['gmx','gmx_mpi']
	for target in targets:
		if is_terminal_command(target)==0: 
			return target
	raise Exception(
		'could not find a gromacs command in the following list: %s.%s'%(
			target,msg))
