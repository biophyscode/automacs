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
def yamlb_special(text,style=None,ignore_json=False):
	unpacked = yamlb(text,style=style,ignore_json=ignore_json)
	#---unpack all leafs in the tree, see if any use pathfinder syntax, and replace the paths
	str_types = [str,unicode] if sys.version_info<(3,0) else [str]
	cataloged = list(catalog(unpacked))
	ununpacked = [(i,j) for i,j in cataloged if type(j) in str_types and re.match('^@',j)]
	#---note that catalog treats lists as terminal items, so we have to check for strings in lists
	alts = [(i,j) for i,j in cataloged if type(j)==list and len(j)>0 
		and all([type(k) in str_types for k in j ])]
	for alt in alts:
		for ii,i in enumerate(alt[1]):
			if re.match('^@',i): ununpacked.append((alt[0]+[ii],alt[1][ii]))
	for route,value in ununpacked:
		#---imports are circular so we put this here
		new_value = get_path_to_module(value)
		delveset(unpacked,*route,value=new_value)
	return unpacked

if not os.path.isfile(state_fn): state = DotDict()
else:
	try: 
		state = DotDict(**json.load(open(state_fn)))
		# convert previous states to DotDict for compatibility
		if 'before' in state.__dict__:
			for bb,b in enumerate(state.before): state.before[bb] = DotDict(**b)
	except: state = DotDict()
if not os.path.isfile(expt_fn): settings,expt = DotDict(),DotDict()
else: 
	expt = DotDict(**json.load(open(expt_fn)))
	try: 
		settings = DotDict(**yamlb_special(expt.settings))
		#---apply overrides to the settings
		if 'settings_overrides' in expt: settings.update(**yamlb_special(expt.settings_overrides))
	except Exception as e:
		print(e) 
		#---note that it is critical that we continue on blanked settings because this
		#---...code is called many times, and only some of these calls actually need settings
		print('[WARNING] settings was broken, now blanked!')
		settings = DotDict()
