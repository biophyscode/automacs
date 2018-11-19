#!/usr/bin/env python

"""
Install ortho via `pip install --ugprade ortho/`
"""
#! deprecated. note that we just access ortho via paths now
#!!! need a plan for installing ortho and other packages without setup.py in root?
raise Exception('deprecated!')
import sys,os
sys.path.insert(0,'../')
from setuptools import setup

setup(name='ortho',
	version='0.1',
	description='Miscellaneous tools.',
	url='http://github.com/bradleyrp/ortho',
	author='Ryan P. Bradley',
	license='GNU GPLv3',
	packages=['ortho','ortho.queue'],
	zip_safe=False)
