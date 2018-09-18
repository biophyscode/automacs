#!/usr/bin/env python

from __future__ import print_function

"""
BOOTSTRAP the AUTOMACS configuration
"""

# default configuration is written to config.json on first make
default_configuration = {
	'commands':['amx/runner','amx/cli.py'],
	'cleanup': ['exec.py','s*-*','state*.json',
		'expt*.json','script*.py','log-*','*.log','v*-*','*.ipynb'],
	'inputs': '@regex^.*?_expts\\.(yaml)$',
	'install_check':'make gromacs_config',
	'experiment_hooks':[('amx.gromacs.experiment_hooks','hook_experiment_modules')],
	}

# directory for current locations of popular modules
git_addresses = {
	'github':'https://github.com/',
	'proteins':'bradleyrp',
	'homology':'ejjordan',
	'bilayers':'bradleyrp',
	'extras':'bradleyrp',
	'docs':'bradleyrp',
	'martini':'bradleyrp',
	'charmm':'bradleyrp',
	'vmd':'bradleyrp',
	'polymers':'bradleyrp',
	'structures':'bradleyrp',}

kickstarters = {

'all':r"""
make set_dict path=\""('modules','inputs/proteins',)"\" value=\""{'address':'%(github)s%(proteins)s/amx-proteins.git','branch':'ortho'}"\"
make set_dict path=\""('modules','inputs/bilayers',)"\" value=\""{'address':'%(github)s%(bilayers)s/amx-bilayers.git','branch':'ortho'}"\"
make set_dict path=\""('modules','inputs/extras',)"\" value=\""{'address':'%(github)s%(extras)s/amx-extras.git','branch':'ortho'}"\"
make set_dict path=\""('modules','inputs/charmm',)"\" value=\""{'address':'%(github)s%(charmm)s/amx-charmm.git'}"\"
make set_dict path=\""('modules','inputs/structure-repo',)"\" value=\""{'address':'%(github)s%(structures)s/amx-structures.git'}"\"
"""%git_addresses,

}

def bootstrap_default(): 
	default_configuration['kickstarters'] = kickstarters
	return default_configuration

def bootstrap_post(): return
