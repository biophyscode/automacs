#!/usr/bin/env python

from __future__ import print_function
import os,sys,ast

class ReExec:
	me = None
	class CodeChunk:
		def __init__(self,code,index=None):
			self.i = index
			if isinstance(code,str): self.this = ast.parse(code)
			else: self.this = code
			self.dump = ast.dump(self.this)
		def dump(self): return ast.dump(self.this)
		def __eq__(self,other):
			return self.dump==other.dump
		def __hash__(self): return hash(self.dump)
		def __repr__(self): return self.dump
	def __init__(self,file):
		globals()['redo'] = self.redo
		ReExec.me = self
		self.text = None
		self.file = file
		self.redo()
	def get_text(self):
		self.text_before = self.text
		with open(self.file) as fp: self.text = fp.read()
	def get_changes(self):
		if not self.text_before: return
		tree_before = ast.parse(self.text_before)
		tree = ast.parse(self.text)
		if ast.dump(tree)==ast.dump(tree_before): print('status','no changes to the script')
		else: 
			print('status','executing changes to %s'%self.file)
			# identify changed nodes in the tree and execute
			# note that this feature reruns any changed child of the script parent
			#! track line numbers are report to the user?
			tree_before,tree = [[self.CodeChunk(i,index=ii) for ii,i in 
				enumerate(ast.iter_child_nodes(ast.parse(t)))]
				for t in [self.text_before,self.text]]
			intersect = set.intersection(set(tree),set(tree_before))
			novel = list(set.difference(set(tree),intersect))
			novel_linenos = set([i.this.lineno for i in novel])
			class CodeSurgery(ast.NodeTransformer):
				def visit(self, node):
					if hasattr(node,'lineno') and node.lineno not in novel_linenos: 
						return ast.parse('last_lineno = %d'%node.lineno).body[0]
					else: return ast.NodeTransformer.generic_visit(self,node)
			code_ready = ast.fix_missing_locations(CodeSurgery().visit(ast.parse(self.text)))
			# run the remainder
			exec(compile(code_ready,filename='<ast>',mode='exec'),globals(),globals())

	def redo(self):
		"""A function which reruns the changed parts of a script. Exported to an interactive script."""
		self.get_text()
		self.get_changes()
	def do(self):
		self.get_text()
		exec(self.text,globals(),globals())

def iteratively_execute():
	"""
	Run this function from a script to enable iterative reexecution.
	Sends the redo function to the main namespace.
	Works well with previous version of `make interact script=path/to/script.py` which used os.system.
	"""
	import __main__
	ie = ReExec(file=__main__.__file__)
	__main__.redo = ie.redo
	__main__.do = ie.do
	__main__.ie = ie

def interact(script='dev.py'): 
	"""Run a script interactively. Should include `ortho.iteratively_execute()`."""
	# previous method: os.system('python -i %s'%(script))
	ie = ReExec(file=script)
	out = globals()
	sys.ps1 = ">>> "
	out.update(**{'ortho':sys.modules['ortho'],'ie':ie,'redo':ie.redo,'do':ie.do})
	# compatible version of execfile
	exec(compile(open(script).read(),filename=script,mode='exec'),out,out)
	import code
	class InteractiveCommand:
		"""Run functions from the repr hence without parentheses. Useful for reeexecution commands."""
		def __init__(self,func,name): self.func,self.name = func,name
		def __repr__(self):
			self.func()
			return '[STATUS] ready'
	# override functions so they can be invoked without parentheses
	do = InteractiveCommand(func=ie.do,name='do')
	redo = InteractiveCommand(func=ie.redo,name='redo')
	# consolidate, add tab completion
	vars = globals()
	vars.update(locals())
	import readline,rlcompleter
	readline.set_completer(rlcompleter.Completer(vars).complete)
	readline.parse_and_bind("tab: complete")
	# interact
	msg = '\n'.join(['[STATUS] %s'%i for i in [
		'entering interactive mode','use "redo" to run changes or "do()" to start from the top']])
	code.interact(local=vars,banner=msg)
