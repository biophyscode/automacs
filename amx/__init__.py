
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
		'generic.py','common.py','calls.py','commands.py','mdp.py',
		'topology_tools.py','structure_tools.py'])],
	'import_rules':[('top','gromacs')]}

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
