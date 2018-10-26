#!/usr/bin/env python

from __future__ import print_function

"""
AUTOMACS RUNNER
Supervise execution.
"""

from .chooser import prep,go,clean

# it is best to expose functions this way instead of decorating them
#   manually in a function call which prevents you from using arguments as flags
#   for example returning prep from avail with args,kwargs means that you
#   could not run `make avail terse` without confusing the prep function into 
#   assuming that terse is an experiment name, since it cannot introspect on
#   the kwargs to see that terse is a boolean flag to the function
avail = prep
