#!/usr/bin/env python

from __future__ import print_function
import os,sys,ast
from .dev import tracebacker

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
	def __init__(self,file,coda=None,namespace=None):
		self.namespace = {} if namespace==None else namespace
		self.namespace['redo'] = self.redo
		ReExec.me = self
		self.text = None
		self.file = file
		self.coda = coda
		#! previously did redo but not sure why self.redo(coda=False)
		#! do does not work self.do(coda=False)
		#! doing the redo sequence manually in case it gets overloaded later on
		self.get_text()
		self.get_changes()
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
			out = self.namespace
			#! exec to eval for python <2.7.15
			eval(compile(code_ready,filename='<ast>',mode='exec'),out,out)
	if False:
		def get_coda(self):
			print('status running coda')
			if self.coda: 
				out = self.namespace
				exec(self.coda,out,out)
	def redo(self):
		"""A function which reruns the changed parts of a script. Exported to an interactive script."""
		self.get_text()
		self.get_changes()
		#if coda: self.get_coda()
	def do(self):
		print('status rerunning the script')
		out = self.namespace
		self.get_text()
		#! testing out exception handling. you always get failure on this line
		try: exec(self.text,out,out)
		except Exception as e: tracebacker(e)
		#if coda: self.get_coda()

def iteratively_execute():
	"""
	Run this function from a script to enable iterative reexecution.
	Sends the redo function to the main namespace.
	Works well with previous version of `make interact script=path/to/script.py` 
	which used os.system.
	"""
	import __main__
	ie = ReExec(file=__main__.__file__)
	__main__.redo = ie.redo
	__main__.do = ie.do
	__main__.ie = ie

def interact(script='dev.py',hooks=None,**kwargs):
	"""Run a script interactively. Should include `ortho.iteratively_execute()`."""
	coda = kwargs.pop('coda',None)
	# allow subclassing of ReExec
	reexec_class = kwargs.pop('reexec_class',ReExec)
	# previous method: os.system('python -i %s'%(script))
	#! out needs the things that globals have but could be replaced
	out = globals()
	ie = reexec_class(file=script,namespace=out)
	sys.ps1 = ">>> "
	if hooks:
		if not isinstance(hooks,tuple): raise Exception('hooks must be a tuple')
		# hooks are applied in order and transform the outgoing dictionary
		# kwargs go through the hook fcuntion
		#! check that the hook is a function
		for hook in hooks: 
			if not callable(hook): raise Exception('hooks must be callable: %s'%hook)
			hook(out,**kwargs)
	out.update(**{'ortho':sys.modules['ortho'],'ie':ie,'redo':ie.redo,'do':ie.do})
	# if a coda exists we execute once to import functions and then again as main
	# note that sending a custom ReExec subclass as in omnicalc go will often implement this kind of coda
	#   in the commands for that class, however, the coda needs to be implemented here, between the 
	#   the execution of the script as not main and then as main in order to have the desired control
	#   flow. hence even though it seems redundant to have a coda here in interact and in the custom 
	#   classes, it is necessary because the initial execution before the code.interact might need to
	#   have this kind of fine-grained control. we do not wish to modify the execution of the code itself
	#   so we compromise by allowing the coda.
	if coda: 
		print('status','executing %s with __name__ = %s'%(script,out['__name__']))
		# compatible version of execfile
		#! exec to eval for python <2.7.15
		eval(compile(open(script).read(),filename=script,mode='exec'),out,out)
		# run the coda once here and note that future execution by ie also runs
		#   the coda afterwards. we run the coda before running as __main__
		#! print('status','interact is running the coda function')
		#! exec to eval for python <2.7.15
		#! exec(coda,out,out)
		eval(compile(coda,'<string>','exec'),out,out)
		out['__name__'] = '__main__'
		print('status','executing %s with __name__ = %s'%(script,out['__name__']))
		#! second execution is a bit redundant, however if we put script code
		#!   inside of a __main__ section per convention, then 
		#! exec to eval for python <2.7.15
		eval(compile(open(script).read(),filename=script,mode='exec'),out,out)
	else:
		out['__name__'] = '__main__'
		# compatible version of execfile
		#! exec to eval for python <2.7.15
		eval(compile(open(script).read(),filename=script,mode='exec'),out,out)
	# prepare the interactive session
	import code
	class InteractiveCommand:
		"""
		Run functions from the repr hence without parentheses. 
		Useful for reeexecution commands.
		"""
		def __init__(self,func,name,prelim=None): 
			self.func,self.name = func,name
			self.prelim = prelim
		def __repr__(self):
			# briefly considered doing this with @property but this works fine
			# currently the prelim feature is deprecated by a subclassed ReExec
			#   but we retain it here as an option
			if self.prelim: 
				#! exec to eval for python <2.7.15
				#! exec(self.prelim,out,out)
				eval(compile(self.prelim,'<string>','exec'),out,out)
			self.func()
			# return empty string but we always get a newline
			return ''
	# apply extra functions if we subclass ReExec to add extra commands
	if kwargs.get('commands',[]):
		collide = [i for i in kwargs['commands'] if i in ['redo','do']]
		if any(collide): 
			#! if you subclass one of the functions in the parent, then we get a name collision that
			#!   prevents the function from executing from the repr
			raise Exception('cannot include commands with these names in a subclass of ReExec: %s'%collide)
		for cmd in kwargs['commands']:
			locals()[cmd] = InteractiveCommand(
				prelim=kwargs.get('do_prelim',None),
				func=getattr(ie,cmd),name=cmd)
	# standard interact gets do and redo
	else:
		# override functions so they can be invoked without parentheses
		do = InteractiveCommand(func=ie.do,name='do',
			# code to run before reexecuting a script from the top with "do"
			prelim=kwargs.get('do_prelim',None))
		redo = InteractiveCommand(func=ie.redo,name='redo')
	# consolidate, add tab completion
	vars = globals()
	vars.update(locals())
	import readline,rlcompleter
	readline.set_completer(rlcompleter.Completer(vars).complete)
	readline.parse_and_bind("tab: complete")
	# interact
	msg = kwargs.get('msg','\n'.join(['[STATUS] %s'%i for i in [
		'entering interactive mode',
		'use "redo" to run changes or "do" to rerun everything']]))
	code.interact(local=vars,banner=msg)
