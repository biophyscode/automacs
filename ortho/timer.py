#!/usr/bin/env python

"""
Set a time limit on processes that might get stuck.

from ortho import time_limit
with time_limit(time_limit_seconds): 
	function_that_might_get_stuck()
"""

import time
import signal
from contextlib import contextmanager

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
	"""Add a time limit to a particular line."""
	def signal_handler(signum,frame): raise (TimeoutException,"Timed out!")
	signal.signal(signal.SIGALRM, signal_handler)
	signal.alarm(seconds)
	try: yield
	finally: signal.alarm(0)
