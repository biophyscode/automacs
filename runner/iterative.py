#!/usr/bin/env python

"""
ITERATIVE

Provides a codeprep function which handles iterative re-execution of your codes. This function looks for an 
error flag in the ``state`` variable, and if it finds one, analyzes the code to see where to continue 
execution. Permanent changes to the ``state`` during failed steps may break this feature, but it's generally
useful for developing complicated simulations.
"""

import ast
from loadstate import state,expt,settings

def codeprep(script_fn='script.py'):
	"""
	Resume execution after a failure without repeating yourself.
	"""
	#---error status triggers a resumption
	if state.get('status',None)=='error':
		with open(script_fn) as fp: script_code = fp.read()
		code = ast.parse(script_code)
		print('[ACME] found an error in the state so we will try to resume')
		#---use abstract syntax trees to avoid repeating already-completed lines
		cmd_old = [i for i in ast.iter_child_nodes(ast.parse(state._error['script_code']))]
		cmd_new = [i for i in ast.iter_child_nodes(ast.parse(script_code))]
		#---get the first different child of root
		diffs = [ii for ii,i in enumerate(cmd_new) if ii<len(cmd_old) and ast.dump(cmd_old[ii])!=ast.dump(i)]
		if len(diffs)==0:
			print('[ACME] script appears identical') 
			if 'last_lineno' not in state._error: 
				raise Exception('identical reexecution but cannot find last_lineno')
			#---if the old and new script are identical we use the recorded last_lineno to find the 
			#---...last successfully executed line and then start on the *next* one
			first_diff = [i.lineno for i in cmd_old].index(state._error['last_lineno'])
			if first_diff>=len(cmd_old)-1: 
				raise Exception('identical reexecution but first difference is after the last line')
			else: first_diff += 1
		else: first_diff = diffs[0]
		#---keep the imports
		import_inds = [ii for ii,i in enumerate(cmd_new) if type(i).__name__=='ImportFrom']
		#---remove the already-completed lines unless they were imports
		remove_linenos = [code.body[i].lineno for i in set(range(first_diff))-set(import_inds)]
		print('[ACME] resuming execution from source code lineno %d'%code.body[first_diff].lineno)
		try: print('[ACME] resuming on function %s'%code.body[first_diff].value.func.id)
		except: pass
		#---use the NodeTransformer to remove linenos below the first different line except the imports
		class CodeSurgery(ast.NodeTransformer):
			def visit(self, node):
				if hasattr(node,'lineno') and node.lineno in remove_linenos: 
					#---note that we advice the lineno instead of returning None here so that the
					#---...post-error executions retain the same line numbering scheme
					return ast.parse('last_lineno = %d'%node.lineno).body[0]
				else: return ast.NodeTransformer.generic_visit(self, node)
		code_ready = ast.fix_missing_locations(CodeSurgery().visit(code))
		#---clean up the previous error
		del state['_error']
	else: 
		#---if there is no error state we get the code from script.py
		with open(script_fn) as fp: script_code = fp.read()
		code = ast.parse(script_code)
		code_ready = code
		#---after each successful root's child execution we update the last_lineno
		new_body = [[k,ast.parse('last_lineno = %d'%k.lineno).body[0]] for k in code_ready.body]
		code_ready = ast.fix_missing_locations(ast.Module(body=[i for j in new_body for i in j]))
	return code_ready
