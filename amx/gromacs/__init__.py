#!/usr/bin/env python

"""
GROMACS INTERFACE MODULE

Provides GROMACS functions to AUTOMACS scripts.

Since this is an automacs module, it is typically imported with the magic_importer function.
This means that anything imported here will be exposed to simulation scripts, however imports 
within this package should be performed in the usual way below.
"""

import os,sys
# protect against makefile inquiries. whenever amx is loaded, this module may be loaded
if os.environ.get('ORTHO_GET_TARGETS',False): pass
else: 

	# IMPORT GROMACS
	before_keys = set(globals().keys())
	
	from ortho import requires_python_check
	# the gromacs.api module inherits from members of YAML so we check the 
	#   module here so you get only a warning on `make` (which runs 
	#   collect_functions) and an error when you try to use GROMACS. note that
	#   any improvement on this would require more careful control of the amx
	#   execution loop because we need to do lots of imports to expose 
	#   command functions via config.json/commands and we need yaml in globals
	#   in modules like gromacs.api and we want to give helpful warnings when
	#   yaml is absent
	try:
		requires_python_check('yaml')
	except: print('warning','GROMACS unavailable until YAML is loaded')
	from .api import gmx

	from .initializer import gromacs_initializer
	from .mdp import write_mdp #!!! needs refactored
	from .fetch import get_pdb # used by @proteins/protein.py
	from .pdb_tools import remove_hetero_atoms # used by @proteins/protein.py
	from .gmx_tools import extract_itp,write_top,write_structure_pdb # used by @proteins/protein.py
	from .bash import write_continue_script # used by @proteins/protein.py
	from .generic import get_start_structure  # used by @proteins/protein.py
	from .generic import interpret_start_structure  # used by @proteins/protein.py @proteins/homology_basic.py
	from .common import minimize,equilibrate
	from .common import solvate_protein,counterions #! legacy needs updated
	from .common import restart_clean

	#! incoming functions
	from .bookkeeping import Landscape

	# import GROMACS functions for automacs 
	#! from .mdp import write_mdp
	#! from .calls import gmx,gmx_run
	#! from .api import gmx
	#from .common import get_pdb,remove_hetero_atoms,extract_itp,write_top,minimize,equilibrate
	#from .common import solvate_protein,counterions,write_structure_pdb,read_gro,dotplace,get_box_vectors
	#from .common import restuff,get_last,
	#from .common import gro_combinator,protein_laden,grouper,atomistic_or_coarse,restart_clean,equilibrate,equilibrate_check,minimize,write_structure_pdb,
	#! if you do this: from .common import *
	#!   then the unique function somehow gets attached to numpy! actually it's not really a mystery why ...
	#!from .common import *
	#! del unique #! hacking around this numpy name collision
	#! from .continue_script import write_continue_script
	#! from .initializer import gromacs_initializer
	#! from .restraints import restraint_maker
	#! from .generic import *
	#!from .structure_tools import *
	# distribute everything imported here as a shared extension
	_shared_extensions = [i for i in list(set(globals().keys())-before_keys) if callable(globals()[i])]

