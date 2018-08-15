#!/usr/bin/env python

from __future__ import print_function
from .bash import bash

import os

def build_docs(source='ortho/docs_source',build='docs',single=False	):
	"""Make documentation."""
	if build=='build_docs': raise Exception('name collision. you cannot build docs in the name of this function: %s'%build)
	opts = []
	if single: opts.append('-b singlehtml')
	bash('sphinx-build -b html %s %s%s'%(source,build,' '+' '.join(opts) if opts else ''),cwd='.')
	index = os.path.abspath(os.path.join(build,'index.html'))
	if not os.path.isfile(index): raise Exception('building docs failed')
	print('status','docs are available at file:///%s'%index)
