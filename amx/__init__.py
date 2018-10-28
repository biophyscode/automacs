#!/usr/bin/env python

"""
AUTOMACS module
reads an experiment and imports necessary codes
"""

from __future__ import print_function
import os,sys,json,ast
import ortho
# python 3 requires relative imports and python 2 needs amx in the path
#   hence we require both sets of imports below
#! figure out why adding amx to the path does not work?
try:
	from . import automacs,utils,importer
	from .legacy import init
	from .state import AMXState
	from .importer import magic_importer,get_import_instructions
	from .reporter import call_reporter
except:
	import automacs,utils,importer
	from legacy import init
	from state import AMXState
	from importer import magic_importer,get_import_instructions
	from reporter import call_reporter

# previously set excepthook to ortho.dev.debug_in_place
# debug in-place by setting config "auto_debug" for ortho.cli
sys.excepthook = ortho.dev.tracebacker

"""
external function refreshes globals
note that this was designed so that we could reload the experiment
  however that would require extra code in a simulation script
  so loading a recently-written experiment when amx was already imported
  was solved by deleting the amx module in the go function, which calls
  the simulation script during supervised execution (i.e. `make go` versus non-supervised 
  execution via `python script.py`). the module deletion is the only way to simulate
  a fresh import of amx, and in this sense helps us to sidestep the convenient feature of 
  python whereby one-loop execution of the prep and execution steps retains amx in memory
  when we really want to simply supervise the script which should run as a standalone.
  see ryan for more details
"""

# state and settings are loaded here
from .automacs import automacs_refresh
globals().update(**automacs_refresh())

# get import instructions from the config
_import_instruct = get_import_instructions(config=ortho.conf)

# generic exports to automacs core
automacs.state = importer.state = state

"""
MAGIC IMPORTS
The following section replaces the acme submodulator a.k.a. importer.py for importing extension modules.
We define the import routing and then send state/settings to the function which collects the extension 
modules, performs any backwashing or side-washing, and then returns exposed functions for the user.
"""

decorate_calls = _import_instruct.pop('decorate',[])
#! gromacs api is imported twice here!?
imported = magic_importer(expt=expt,instruct=_import_instruct,
	distribute=dict(state=state,settings=settings,expt=expt))
globals().update(**imported['functions'])

# run initializer functions on the state
if 'initializers' in imported: 
	for initializer_name in imported['initializers']: 
		imported['initializers'][initializer_name](state=state)

# decorate specific functions with the call_reporter after we have the state
for funcname in decorate_calls.get('functions',[]):
	globals()[funcname] = call_reporter(func=globals()[funcname],state=state)

# special deep-dive call reporters for internal functions not called from the automacs script
#! note that we cannot easily replace these functions without sys.modules
for base,funcname in decorate_calls.get('subs',[]):
	sys.modules['amx.%s'%base].__dict__[funcname] = call_reporter(
		func=sys.modules['amx.%s'%base].__dict__[funcname],state=state)

from .automacs import automacs_execution_handler
automacs_execution_handler(namespace=globals())
