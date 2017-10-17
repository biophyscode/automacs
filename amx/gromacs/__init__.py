#!/usr/bin/env python

#from mdp import write_mdp
#from topology_tools import GMXTopology

_not_reported = ['dotplace']

#---elevate some items for automacs.py
from calls import gmx,gmx_get_paths
from commands import gmx_call_templates,gmx_get_last_call,gmx_commands_interpret
