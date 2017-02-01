#!/usr/bin/env python

"""
LOADSTATE

Read expt.json and state.json into ``expt`` and ``state`` variables which are shared throughout any ACME-style
simulations. We also unpack the ``settings`` item from ``expt`` and load it into a third shared variable. The
get_path_to_module function from acme.py also applies any "@"-prefixed syntax sugar for looking up relative
paths from the ACME config.py file.
"""

#---we *always* only import expt.json
#---the user or metarun must copy to expt.json for execution
state_fn = 'state.json'
expt_fn = 'expt.json'

import os,sys,json,re
from datapack import DotDict,yamlb,catalog,delveset
from acme import get_path_to_module

#---every use of yamlb on settings in the acme scheme requires some decoration
#---...thankfully this only happens twice: once here (where most imports of expt.json happen)
#---...and once in acme itself, when the experiment is written and the settings are updated
#---...!!! that is temporarily disabled for now
def yamlb_special(yamlb,text,style=None,ignore_json=False):
	unpacked = yamlb(text,style=style,ignore_json=ignore_json)
	#---unpack all leafs in the tree, see if any use pathfinder syntax, and replace the paths
	ununpacked = [(i,j) for i,j in catalog(unpacked) if type(j)==str and re.match('^@',j)]
	for route,value in ununpacked:
		#---imports are circular so we put this here
		new_value = get_path_to_module(value)
		delveset(unpacked,*route,value=new_value)
	return unpacked

if not os.path.isfile(state_fn): state = DotDict()
else:
	try: state = DotDict(**json.load(open(state_fn)))
	except: state = DotDict()
if not os.path.isfile(expt_fn): settings,expt = DotDict(),DotDict()
else: 
	expt = DotDict(**json.load(open(expt_fn)))
	try: settings = DotDict(**yamlb_special(yamlb,expt.settings))
	except: 
		print('[WARNING] settings was broken, now blanked!')
		settings = DotDict()
