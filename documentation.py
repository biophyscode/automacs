#!/usr/bin/env python

from __future__ import print_function
from .bash import bash
from .config import read_config

import os

def build_docs(source='ortho/docs_source',build='docs',single=False	):
	"""Make documentation."""
	if build=='build_docs': 
		raise Exception('name collision. you cannot build docs in the name of this function: %s'%build)
	docs_default = {'local':{'source':source,'build':build}}
	conf = read_config()
	if conf.get('docs',{}).get('list',None): 
		print('warning','overriding source, build arguments to write the docs according to the config')
	docs = conf.get('docs',{}).get('list',docs_default)
	# command-line options
	opts = []
	if single: opts.append('-b singlehtml')
	# iterate over docs to make
	urls = {}
	for name,detail in docs.items():
		source,build = detail['source'],detail['build']
		bash('sphinx-build -b html %s %s%s'%(source,build,' '+' '.join(opts) if opts else ''),cwd='.')
		index = os.path.abspath(os.path.join(build,'index.html'))
		if not os.path.isfile(index): raise Exception('building docs "%s" failed'%name)
		urls[name] = index
	for name,index in urls.items(): print('status','docs are available at file:///%s'%index)
