#!/usr/bin/env python

"""
GROMACS INTERFACE MODULE

Provides GROMACS functions to AUTOMACS scripts.

Since this is an automacs module, it is typically imported with the magic_importer function.
This means that anything imported here will be exposed to simulation scripts, however imports 
within this package should be performed in the usual way below.
"""

import os,sys
# protect against makefile inquiries
if os.environ.get('ORTHO_GET_TARGETS',False): pass
else: 
	# import GROMACS functions for automacs 
	from .mdp import write_mdp
	from .calls import gmx,gmx_run
	from .common import get_pdb,remove_hetero_atoms,extract_itp,write_top,minimize,equilibrate
	from .common import solvate_protein,counterions,write_structure_pdb
	from .continue_script import write_continue_script
	from .initializer import gromacs_initializer
