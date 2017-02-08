#!/usr/bin/env python -B
{'acme': './runner',
 'cleanup': ['exec.py', 's*-*', 'state*.json', 'expt*.json', 'script*.py', 'log-*', '*.log', 'v*-*'],
 'commands': ['runner/control.py', 'runner/datapack.py', 'amx/cli.py', 'inputs/docs/docs.py'],
 'commands_aliases': [('prep?', 'preplist'), ('set', 'set_config')],
 'inputs': '@regex^.*?_expts\\.py$',
 'install_check': 'make gromacs_config',
 'modules': [('http://github.com/bradleyrp/amx-proteins.git', 'amx/proteins'),
             ('http://github.com/bradleyrp/amx-extras.git', 'inputs/extras'),
             ('http://github.com/bradleyrp/amx-docs.git', 'inputs/docs'),
             ('http://github.com/bradleyrp/amx-vmd.git', 'inputs/vmd'),
             ('http://github.com/bradleyrp/amx-bilayers.git', 'inputs/bilayers'),
             ('http://github.com/bradleyrp/amx-martini.git', 'inputs/martini'),
             ('http://github.com/bradleyrp/amx-charmm.git', 'inputs/charmm')]}