#!/usr/bin/env python

"""
ACME (a.k.a. the simulation runner)

The ACME code is a framework for running simulations from readable python scripts.
These codes were designed to coordinate AUTOMACS simulations and supply a number of useful design constraints
that (hopefully) make it easy to share, customize, and reproduce simulation codes on different machines.
The name "ACME" has no particular meaning.

the ACME framework provides:

1. A generic framework for requesting experiments.
2. A generic method for running these experiments from the command line.
2. A simple method for reusing codes without copying them or managing paths.
3. A single, shared namespace for transmitting data between functions.
4. Iterative reexecution for developing costly simulation codes without repeating yourself.

a critcal note about locations:

The ACME codes (housed here in a folder probably called "runner") can be placed *anywhere* in your code as 
long as you follow a few simple rules. Any instances of "connect to runner" in the comments indicate a 
connection to ACME. The current state of these connections is summarized below.

1. The config.py specifies an "acme" flag which provides the path here. 
2. This __init__.py file always adds itself to sys.path so its submodules can import from each other.
3. executor.py runs our codes (possibly re-iteratively, during development) using ACME functions.
4. makefile uses ACME functions to find python functions that the user can run from the command line
5. Some modules like docs.py use ACME to parse the other codes and produce "live" documentation
6. Other modules like vmd use ACME to get the simulation states without running ACME itself

All of the examples above contain a "connect to runner" in the comments. Several of them locate these codes by
checking the "acme" key in config.py, which specifies our location. They "search upward" until they find 
config.py. Most ACME functionality is imported via "from runner import NAME" statements. Only top-level 
modules, like AUTOMACS itself, contained in `amx`, will import the entire module. AUTOMACS does this in a 
customied block in __init__.py which itself executes importer.py and handles the shared namespaces and 
framework features listed above.
"""

import os,sys

#---note that all imports within runner require a path to runner so we add it to the path below

#---search upwards to find config.py in a parent directory
root_dns = [os.path.abspath(os.path.join(__file__,*('..' for j in range(i+1)))) for i in range(5)]
try: root_dn = next(f for f in root_dns if os.path.isfile(os.path.join(f,'config.py')))
except: raise Exception('cannot find config.py in any (reasonable) parent of %s'%__file__)
config = {}
with open(os.path.join(root_dn,'config.py')) as fp: config = eval(fp.read())
#---connect to runner
sys.path.insert(0,config['acme'])

#---universal ACME functions required throughout acme-inflected modules
from . datapack import DotDict
from . states import call_reporter,finished

#---read importer.py for use in __init__.py for top-level acme-inflected modules
import os
with open(os.path.join(os.path.dirname(__file__),'importer.py')) as fp: 
	acme_submodulator = fp.read()

#---always import the state to the highest level in the namespace
from loadstate import state,expt,settings
