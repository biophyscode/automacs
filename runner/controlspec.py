#!/usr/bin/env python

"""
CONTROL SPECIFICATION
---------------------

This code includes only a single variable called ``controlspec``, which provides instructions for validating experiments so that they are fully specified at runtime. The ``controlspec['keysets']`` variables provides sets of keys (ironically for the ``_keysets`` function in ``control.py``), at least one which must match with the keys in each experiment. See :any:`control.py <control>` for more details; this code uses the ``controlspec`` variable to direct the execution.

.. make sure that the lines argument in the docstring starts at the line where controlspec starts
.. note that the path below assumes these docs are at inputs/docs and the runner is in the root
.. the replace directive does not work in other directives so this would be hard to make automatic

The ``controlspec`` variable below sets the required keys for different run types. For example, the first of the ``keysets`` tells you that any ``run`` must contain the following keys: ``['script','extensions','params','tags','settings','cwd']``. These keys are always required (though some can be ``None`` or empty lists) and ensure that the correct ``script`` is executed with the right ``settings``.

.. literalinclude:: ../../../runner/controlspec.py
	:tab-width: 2
	:lines: 31-

"""

controlmsg = {
	'json':'found either (a) repeated keys or (b) JSON error in a string. '+
		'we require incoming dict literals to be convertible to JSON '+
		'so we can check for repeated keys. this means that single quotes must be converted to '+
		'double quotes, which means that you should use escaped double quotes where possible. '+
		'see the jsonify function for more information on how things are checked. otherwise '+
		'try `make codecheck <file>` to debug the JSON error in your file. ',}

controlspec = {
	'keysets':{
		'comment':{('comment'):'comment'},
		'run':{
			('script','extensions','params','tags','settings','cwd'):'std',
			('script','extensions','params','tags','settings','cwd','prelude'):'std'},
		'metarun':{('metarun','cwd'):True,('metarun','cwd','tags'):True,
			('metarun','cwd','tags','prelude'):True,
			('metarun','cwd','prelude'):True},
		'metarun_steps':{
			('step','do'):'simple',
			('quick','settings'):'quick',
			('quick','settings','jupyter_coda'):'quick',
			('step','do','settings'):'settings',},
		'quick':{
			('quick',):'quick',
			('quick','jupyter_coda'):'quick',
			('quick','cwd',):'quick',
			('quick','settings','cwd'):'basic',
			('quick','settings','cwd','tags'):'basic',
			('quick','settings','cwd','params','extensions','tags'):'extensions',
			('quick','settings','cwd','params','extensions','tags','imports'):'extensions_imports'},},}
