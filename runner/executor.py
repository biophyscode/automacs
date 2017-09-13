#!/bin/bash
"exec" "python" "-B" "$0" "$@"

"""
ACME EXECUTOR
Runs acme scripts with iterative reexecution and save states.
"""

import os,sys,json,ast,re
#---executor path is hard-coded here
#---connect to runner
sys.path.insert(0,"PATH_TO_RUNNER")
from datapack import DotDict,yamlb
from states import stopper,finished
from iterative import codeprep
from loadstate import state,expt,settings
#---NOTE THAT exec.py IS AUTOMATICALLY EDITED BY runner.py to include the script name
#---define script_fn here
code_ready = codeprep(script_fn=script_fn)
last_lineno = -1
try: exec(compile(code_ready,filename='<ast>',mode='exec'))
except (KeyboardInterrupt,Exception) as e: 
	if 'state' in globals() or ('amx' in globals() and hasattr(globals()['amx'],'state')): 
		if 'state' in globals(): this_state = state
		else: this_state = amx.state
		#---errors in the supervised execution are inscrutable so we provide a line number here
		print('%s %s'%(fab('[ERROR]','red_black'),
			'caught the following error at line %s of the supervised script %s'%(
			last_lineno+1,script_fn)))
		#---DO NOT CHANGE THE STOPPER WITHOUT CONSULTING EXECUTOR FUNCTION
		stopper(this_state,e,script_fn=script_fn,last_lineno=last_lineno)
	else: 
		import sys,traceback
		exc_type,exc_obj,exc_tb = sys.exc_info()
		tracetext = re.sub(r'\\n','\\n[TRACEBACK] ',str(''.join(traceback.format_tb(exc_tb))))
		tracetext = '[TRACEBACK]'+tracetext.strip()
		sys.stdout.write(tracetext+'\\n')
		sys.stdout.write('[ERROR] exception before state is available: %s\\n'%e)
	#---this error lacks the fancy formatting but tells you if the problem is in the parent script
	#---! note that this will only catch functions, not e.g. shutil.copyfile
	#---! note that sometimes the lineno is off by one, which is hard to explain? tried correcting below
	try: print('[NOTE] caught exception on script function: %s'%code_ready.body[last_lineno-1].value.func.id)
	except: pass
	sys.exit(1)
else: finished(state,script_fn=script_fn)
