#!/usr/bin/env python -B
{'acme': './runner',
 'cleanup': ['exec.py', 's*-*', 'state*.json', 'expt*.json', 'script*.py', 'log-*', '*.log', 'v*-*'],
 'commands': ['runner/control.py', 'runner/datapack.py', 'amx/cli.py'],
 'commands_aliases': [('prep?', 'preplist'), ('set', 'set_config')],
 'inputs': '@regex^.*?_expts\\.py$',
 'install_check': 'make gromacs_config',
 'modules': []}