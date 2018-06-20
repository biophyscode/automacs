#!/usr/bin/env python

"""
AUTOMACS command-line interface
"""

from __future__ import print_function

__all__ = ['prep','clean','go']

# store the CLI functions in runner because they are interdependent
from runner import prep,clean,go
