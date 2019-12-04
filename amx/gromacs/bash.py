#!/usr/bin/env python

import os,re

def write_continue_script(**kwargs):
	"""
	Make a continue script
	"""
	mode = kwargs.pop('mode','extend')
	until = kwargs.pop('until',1000000)
	extend = kwargs.pop('extend',1000000)
	if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
	#! this path is failing because we are in inputs/bilayers/codes
	#! template = os.path.join(__file__,'continue-gmx-2018.sh')
	template = os.path.join('amx','gromacs','continue-gmx-2018.sh')
	with open(template) as fp: raw = fp.read()
	sub = '\n'.join([
		'# settings injected by write_continue_script',
		'MODE="%s"'%mode,
		'EXTEND=%d'%extend,
		'UNTIL=%d'%until,])
	raw = re.sub('^# injected settings go here',sub,raw,flags=re.M+re.DOTALL)
	with open(state.here+'script-continue.sh','w') as fp: fp.write(raw)
