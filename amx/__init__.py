#!/usr/bin/env python

"""
AUTOMACS importer for ACME

This file runs the contents of importer.py in order to allow acme-inflected codes to share this (amx) module
in a manner that allows intelligent imports, flexible and modular experiments, and a unified namespace.

Note: this is a highly overloaded python environment. See the ACME documentation for more details.
Note: this docstring is not caught by sphinx.
Note: import instructions for amx are below.
"""

import os
_import_instruct = {
	'special_import_targets':[('top',['automacs.py','cli.py','utils.py']),
		('gromacs',['gromacs%s%s'%(os.path.sep,i) for i in 
		#---! rename common and other generic names or conflict when you develop lammps
		['generic.py','common.py','calls.py','gromacs_commands.py','mdp.py',
		'topology_tools.py','structure_tools.py','continue_script.py','postprocess.py',
		'restraints.py','force_field_tools.py']]),
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
		#---! move the machine configuration to amx and generalize it?
		{'source':'calls.py','target':'lammps.py','name':'gmx_get_machine_config'},][:-1],
	#---! need more central handling of the command templates
	##### MAJOR HACK FOR USE IN OMNICALC
	'coda':"exec(open('amx/amx/gromacs/command_templates.py','r').read(),subs['automacs.py'].__dict__)"}

#---import the runner and auto-import this module (if not sphinx)
import os,sys,shutil
if not os.path.basename(sys.argv[0])=='sphinx-build':
	#---find config.py in a parent directory
	root_dns = [os.path.abspath(os.path.join(__file__,*('..' for j in range(i+1)))) for i in range(5)]
	try: root_dn = next(f for f in root_dns if os.path.isfile(os.path.join(f,'config.py')))
	except: raise Exception('cannot find config.py in any (reasonable) parent of %s'%__file__)
	config = {}
	with open(os.path.join(root_dn,'config.py')) as fp: config = eval(fp.read())
	#---connect to runner
	sys.path.insert(0,os.path.abspath(os.path.dirname(config['acme'])))
	acme_mod = __import__(os.path.basename('runner'))
	reqs = 'DotDict,state,settings,expt,call_reporter,acme_submodulator,finished'.split(',')
	globals().update(**dict([(k,acme_mod.__dict__[k]) for k in reqs]))
	exec(acme_submodulator)
