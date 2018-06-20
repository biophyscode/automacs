#!/usr/bin/env python

"""
AUTOMACS module
reads an experiment and imports necessary codes
"""

from __future__ import print_function
import os,sys,json
#! relative imports fail here
import automacs,utils,importer
from legacy import init
from state import AMXState
from importer import magic_importer
import ortho

# debugger via flag from environment or from conf
try: do_debug_env = eval(os.environ.get('DEBUG','False')) 
except: do_debug_env = False
if ortho.conf.get('debug',do_debug_env)==True: sys.excepthook = ortho.dev.debug_in_place
else: sys.excepthook = ortho.dev.tracebacker

# load experiment and state
if not os.path.isfile('expt.json'): raise Exception('cannot import automacs without expt.json')
_has_state = os.path.isfile('state.json')
if _has_state: print('status','found a previous state at state.json')

"""
DEV NOTES!!!
previous method moved expt_1.json to expt.json so it would be read 
	and automatically read state.json if available
since we have no information on why automacs was imported we have to do some inference
the run functions in execution.py should handle the exceptions so that we always have the right files here
use ortho to direct automacs?
needs:
- tracebacker?
- magic imports i.e. acme submodulator
"""

settings = AMXState(me='settings')
state = AMXState(me='state',fallbacks=[settings])
with open('expt.json') as fp: 
	# the expt variable has strict attribute lookups
	expt = AMXState(me='expt',except_on_missing=True,**json.load(fp))
expt.meta = AMXState(me='expt.meta',except_on_missing=True,**expt.pop('meta'))
settings.update(**expt.get('settings',{}))
if _has_state: print('dev','get the state here!')

#! automacs-general imports happen with `import automacs` above
#! export manually
#! this should be replaced with an automacs.py entry in the import router
automacs.state = state
automacs.settings = settings
make_step = automacs.make_step
copy_file = automacs.copy_file
status = utils.status
importer.state = state

#!!! deprecated module routing
_import_instruct = {
	'special_import_targets':[('top',['automacs.py','cli.py','utils.py']),
		('gromacs',['gromacs%s%s'%(os.path.sep,i) for i in 
		#! rename common and other generic names or conflict when you develop lammps
		'generic.py','common.py','calls.py','gromacs_commands.py','mdp.py',
		'topology_tools.py','structure_tools.py','continue_script.py','postprocess.py',
		'restraints.py','force_field_tools.py']),
		('lammps',['lammps/lammps.py'])
		,][:-1], #! lammps is on a branch for now
	'import_rules':[('top','gromacs'),('top','lammps')][:-1], #! lammps is on a branch for now
	'import_rules_explicit':[
		{'source':'calls.py','target':'continue_script.py','name':'gmx_get_paths'},
		{'source':'calls.py','target':'cli.py','name':'gmx_get_machine_config'},
		{'source':'continue_script.py','target':'cli.py','name':'write_continue_script_master'},
		{'source':'calls.py','target':'automacs.py','name':'gmx_get_paths'},
		{'source':'gromacs_commands.py','target':'automacs.py','name':'gmx_commands_interpret'},
		{'source':'gromacs_commands.py','target':'postprocess.py','name':'gmx_commands_interpret'},
		{'source':'calls.py','target':'postprocess.py','name':'gmx'},
		{'source':'gromacs_commands.py','target':'calls.py','name':'gmx_convert_template_to_call'},
		{'source':'gromacs_commands.py','target':'postprocess.py','name':'gmx_get_last_call'},
		#! move the machine configuration to amx and generalize it?
		{'source':'calls.py','target':'lammps.py','name':'gmx_get_machine_config'},][:-1],
	#! need more central handling of the command templates
	'coda':"exec(open('amx/gromacs/command_templates.py','r').read(),subs['automacs.py'].__dict__)"}

# module routing
_import_instruct = {
	'modules':['gromacs'],
	'decorate':{'functions':['gmx'],'subs':[('gromacs.calls','gmx_run')]},
	'initializers':['gromacs_initializer']}

# allow conf to override the import instructions
_import_instruct = ortho.conf.get('_import_instruct',_import_instruct)

"""
MAGIC IMPORTS
The following section replaces the acme submodulator a.k.a. importer.py for importing extension modules.
We define the import routing and then send state/settings to the function which collects the extension 
modules, performs any backwashing or side-washing, and then returns exposed functiosn for the user.
"""

decorate_calls = _import_instruct.pop('decorate',[])
imported = magic_importer(expt=expt,instruct=_import_instruct,
	distribute=dict(state=state,settings=settings,expt=expt))
globals().update(**imported['functions'])

# run initializer functions on the state
if 'initializers' in imported: 
	for initializer_name in imported['initializers']: 
		imported['initializers'][initializer_name](state=state)

# decorate specific functions with the call_reporter after we have the state
if decorate_calls: from reporter import call_reporter
for funcname in decorate_calls.get('functions',[]):
	globals()[funcname] = call_reporter(func=globals()[funcname],state=state)
# special deep-dive call reporters for internal functions not called from the automacs script
#! note that we cannot easily replace these functions without sys.modules
for base,funcname in decorate_calls.get('subs',[]):
	sys.modules['amx.%s'%base].__dict__[funcname] = call_reporter(
		func=sys.modules['amx.%s'%base].__dict__[funcname],state=state)
