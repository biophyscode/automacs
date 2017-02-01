#!/usr/bin/env python

"""
CONTROL SPECIFICATION

Provide instructions for validating experiments. The ``controlspec['keysets']`` variables provides sets of 
keys (ironically for the ``_keysets`` function in ``control.py``), at least one which must match with the keys
in each experiment. See ``control.py`` for more details.
"""

controlspec = {
	'keysets':{
		'run':{('script','extensions','params','tags','settings','cwd'):'std'},
		'metarun':{('metarun','cwd'):True},
		'metarun_steps':{
			('step','do'):'simple',
			('step','do','settings'):'settings',},
		'quick':{
			('quick',):'quick',
			('settings','cwd','quick'):'basic',
			('settings','cwd','quick','params','extensions','tags'):'extensions',
			('settings','cwd','quick','params','extensions','tags','imports'):'extensions_imports'},},
	'msg':{
		'json':'found either (a) repeated keys or (b) JSON error in a string. '+
			'we require incoming dict literals to be convertible to JSON '+
			'so we can check for repeated keys. this means that single quotes must be converted to '+
			'double quotes, which means that you should use escaped double quotes where possible. '+
			'see the jsonify function for more information on how things are checked. otherwise '+
			'try `make codecheck <file>` to debug the JSON error in your file. ',},}
