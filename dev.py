#!/usr/bin/env python

"""
ORTHO
development tools
"""

import sys,re,traceback
from .misc import say

def tracebacker(e):
	"""Standard traceback handling for easy-to-read error messages."""
	exc_type,exc_obj,exc_tb = sys.exc_info()
	tag = say('[TRACEBACK]','gray')
	tracetext = tag+' '+re.sub(r'\n','\n%s'%tag,str(''.join(traceback.format_tb(exc_tb)).strip()))
	print(say(tracetext))
	print(say('[ERROR]','red_black')+' '+say('%s'%e,'cyan_black'))
