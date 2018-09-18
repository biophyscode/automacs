#!/usr/bin/env python

import re

def hook_experiment_modules(raw,config):
	"""Handle the @-syntax on experiment modules by looking them up in config.json."""
	subs = {}
	for spot,_ in config.get('modules',{}).items():
		key,val = spot.split('/')[-1],spot
		if key in subs: raise Exception('repeated module child name %s'%key)
		subs[key] = val
	for key,val in subs.items():
		raw = re.sub('@%s'%key,val,raw)
	return raw
