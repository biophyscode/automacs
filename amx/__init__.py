#!/usr/bin/env python

"""
AUTOMACS module
reads an experiment and imports necessary codes
"""

from __future__ import print_function
import os,sys,json,ast
import ortho

if sys.version_info<(3,0): from automacs import automacs_refresh
else: from .automacs import automacs_refresh
result = automacs_refresh()
# add the state,settings,expt variables here
globals().update(**result)

# python 3 requires relative imports and python 2 needs amx in the path
#   hence we require both sets of imports below
if sys.version_info<(3,0): 
	from importer import magic_importer,get_import_instructions
else: 
	from .importer import magic_importer,get_import_instructions

# previously set excepthook to ortho.dev.debug_in_place
# debug in-place by setting config "auto_debug" for ortho.cli
sys.excepthook = ortho.dev.tracebacker

# determine if automacs is the subject or the object
is_subject = (os.path.basename(os.path.abspath(os.path.join(
	os.path.dirname(__file__),'..')))==os.path.basename(os.getcwd()))
if not is_subject:
	remote_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
	#  we change directory to get the right config and because the modules 
	#    section framework is relative paths. note that any code which
	#    uses automacs remotely must run os.chdir afterwards. see the code at
	#    omni.base.utils for an example of this, in which the imported
	#    functions are decorated to manage this later on
	os.chdir(remote_path)
	config = ortho.read_config()
else: config = ortho.conf

# get import instructions from the config
# previously we exported the state after this line. now it is imported
_import_instruct = get_import_instructions(config=config)

"""
MAGIC IMPORTS
The following section replaces the acme submodulator a.k.a. importer.py for importing extension modules.
We define the import routing and then send state/settings to the function which collects the extension 
modules, performs any backwashing or side-washing, and then returns exposed functions for the user.
"""
decorate_calls = _import_instruct.pop('decorate',[])
imported = magic_importer(expt=expt,instruct=_import_instruct,
	distribute=dict(state=state,settings=settings,expt=expt))
globals().update(**imported['functions'])
# run initializer functions (state should be distributed there)
if 'initializers' in imported: 
	for initializer_name in imported['initializers']: 
		imported['initializers'][initializer_name]()
# supervised execution interrupts here
from .automacs import automacs_execution_handler
automacs_execution_handler(namespace=globals())
