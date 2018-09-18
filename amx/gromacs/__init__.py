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
	before_keys = set(globals().keys())
	# import GROMACS functions for automacs 
	from .mdp import write_mdp
	from .calls import gmx,gmx_run
	#from .common import get_pdb,remove_hetero_atoms,extract_itp,write_top,minimize,equilibrate
	#from .common import solvate_protein,counterions,write_structure_pdb,read_gro,dotplace,get_box_vectors
	#from .common import restuff,get_last,
	#from .common import gro_combinator,protein_laden,grouper,atomistic_or_coarse,restart_clean,equilibrate,equilibrate_check,minimize,write_structure_pdb,
	#! if you do this: from .common import *
	#!   then the unique function somehow gets attached to numpy! actually it's not really a mystery why ...
	from .common import *
	del unique #! hacking around this numpy name collision
	from .continue_script import write_continue_script
	from .initializer import gromacs_initializer
	from .restraints import restraint_maker
	from .generic import *
	# distribute everything imported here as a shared extension
	_shared_extensions = [i for i in list(set(globals().keys())-before_keys) if callable(globals()[i])]
