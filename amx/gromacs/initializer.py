#!/usr/bin/env python

from __future__ import print_function

#from .gromacs_commands import gmx_commands_interpret
#from .command_templates import gmx_call_templates
# from .calls import gmx_get_paths
from .api import gmx_get_paths

def gromacs_initializer(state):
	"""
	Prepare the state for running GROMACS simulations.
	"""
	return #!!!!!!!!! disabled for now

	state.gmxcalls = gmx_commands_interpret(gmx_call_templates)
	try: gmx_get_paths()
	except: print('warning','no gromacs paths available. try `make gromacs_config` to remedy')
