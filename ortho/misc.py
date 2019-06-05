#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
import os,sys,re,json,time,collections

# adjucate string types between versions. use `type(a) in str_types` for light scripting
# this is a legacy solution consistent with basestring or six.string_types
# we skip six.string_types because it has the same role as the following
# recommended string checking is via isinstance(u'string',basestring)
basestring = string_types = str_types = (str,unicode) if sys.version_info<(3,0) else (str,)
str_types_list = list(str_types)

def listify(x): 
	"""Turn a string or a list into a list."""
	if isinstance(x,basestring): return [x]
	elif isinstance(x,list): return x
	elif isinstance(x,tuple): return x
	else: raise Exception(
		'listify takes a string, list, tuple but got: %s'%type(x))

def unique(items):
	"""
	Enforce uniqueness on a list.
	"""
	try: (element,) = items
	except ValueError: 
		raise Exception('expecting only one item in this list: %s'%str(items))
	return element

def uniform(items):
	return unique(set(items))

def asciitree(obj,depth=0,wide=2,last=[],recursed=False):
	"""
	Print a dictionary as a tree to the terminal.
	Includes some simuluxe-specific quirks.
	"""
	corner = u'\u251C'
	corner_end = u'\u2514'
	horizo,horizo_bold = u'\u2500',u'\u2501'
	vertic,vertic_bold = u'\u2502',u'\u2503'
	tl,tr,bl,br = u'\u250F',u'\u2513',u'\u2517',u'\u251B'
	spacer_both = dict([(k,{
		0:'\n',1:(' '*(wide+1)*(depth-1)+c+horizo*wide),
		2:' '*(wide+1)*(depth-1)}[depth] if depth <= 1 
		else (''.join([(vertic if d not in last else ' ')+
		' '*wide for d in range(1,depth)]))+c+horizo*wide) 
		for (k,c) in [('mid',corner),('end',corner_end)]])
	spacer = spacer_both['mid']
	if type(obj) in [float,int,bool]+str_types_list:
		if depth == 0: print(spacer+str(obj)+'\n'+horizo*len(obj))
		else: print(spacer+str(obj))
	elif isinstance(obj,dict) and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) in [list,tuple]:
		for ind,item in enumerate(obj):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(item) in [float,int,bool]+str_types_list: print(spacer_this+str(item))
			elif item != {}:
				print(spacer_this+'('+str(ind)+')')
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print('unhandled tree object %s'%item)
	elif isinstance(obj,dict) and obj != {}:
		for ind,key in enumerate(obj.keys()):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(obj[key]) in [float,int,bool]+str_types_list: print(spacer_this+str(key)+' = '+str(obj[key]))
			# special: print single-item lists of strings on the same line as the key
			elif type(obj[key])==list and len(obj[key])==1 and type(obj[key][0]) in [str,float,int,bool]:
				print(spacer_this+key+' = '+str(obj[key]))
			# special: skip lists if blank dictionaries
			elif type(obj[key])==list and all([i=={} for i in obj[key]]):
				print(spacer_this+key+' = (empty)')
			elif obj[key] != {}:
				# fancy border for top level
				if depth == 0:
					print('\n'+tl+horizo_bold*(len(key)+0)+
						tr+spacer_this+vertic_bold+str(key)+vertic_bold+'\n'+\
						bl+horizo_bold*len(key)+br+'\n'+vertic)
				elif obj[key]==None: print(spacer_this+key+' = None')
				else: print(spacer_this+key)
				if obj[key]!=None: 
					asciitree(obj[key],depth=depth+1,
						last=last+([depth] if ind==len(obj)-1 else []),
						recursed=True)
			elif type(obj[key])==list and obj[key]==[]:
				print(spacer_this+'(empty)')
			elif obj[key]=={}: print(spacer_this+'%s = {}'%key)
			else: print('unhandled tree object %s'%key)
	else: print('unhandled tree object %s'%obj)
	if not recursed: print('\n')

def treeview(data,style=None):
	"""
	Print a tree in one of several styles.
	"""
	if not style: style = conf.get('tree_style','unicode')  # pylint: disable=undefined-variable
	if style=='unicode': 
		# protect against TeeMultiplexer here because it cannot print unicode to the log file
		do_swap_stdout = sys.stdout.__class__.__name__=='TeeMultiplexer'
		do_swap_stderr = sys.stderr.__class__.__name__=='TeeMultiplexer'
		if do_swap_stdout: 
			hold_stdout = sys.stdout
			#! assume fd1 is the original stream
			sys.stdout = sys.stdout.fd1
		if do_swap_stderr: 
			hold_stderr = sys.stderr
			#! assume fd1 is the original stream
			sys.stderr = sys.stderr.fd1
		# show the tree here
		asciitree(data)
		# swap back
		if do_swap_stderr: sys.stderr = hold_stderr
		if do_swap_stdout: sys.stdout = hold_stdout
	elif style=='json': return print(json.dumps(data))
	elif style=='pprint': 
		import pprint
		return pprint.pprint(data)
	else: raise Exception('invalid style %s'%style)

def say(text,*flags):
	"""Colorize the text."""
	# three-digit codes: first one is style (0 and 2 are regular, 3 is italics, 1 is bold)
	colors = {'gray':(0,37,48),'cyan_black':(1,36,40),'red_black':(1,31,40),'black_gray':(0,37,40),
		'white_black':(1,37,40),'mag_gray':(0,35,47)}
	# no colors if we are logging to a text file because nobody wants all that unicode in a log
	if flags and hasattr(sys.stdout,'isatty') and sys.stdout.isatty()==True: 
		if any(f for f in flags if f not in colors): 
			raise Exception('cannot find a color %s. try one of %s'%(str(flags),colors.keys()))
		for f in flags[::-1]: 
			style,fg,bg = colors[f]
			text = '\x1b[%sm%s\x1b[0m'%(';'.join([str(style),str(fg),str(bg)]),text)
	return text

def locate(keyword):
	"""
	Locate the source code for a python function which is visible to the controller.

	Parameters
	----------
	keyword : string
		Any part of a function name (including regular expressions)

	Notes
	-----
	This controller script is grepped by the makefile in order to expose its python functions to the makefile
	interface so that users can run e.g. "make program protein" in orer to access the ``program`` function
	above. The ``makeface`` function routes makefile arguments and keyword arguments into python's functions.
	The makefile also detects python functions from any scripts located in amx/procedures/extras.
	The ``locate`` function is useful for finding functions which may be found in many parts of the automacs
	directory structure.
	"""
	os.system((r'find . -name "*.py" -not -path "./env/*" '+
		r'| xargs egrep -i --color=always "(def|class) \w*%s\w*"')%keyword)

class ColorPrinter:
	"""
	Write colorful text to terminal.
	To use ColorPrinter in a script, include:
		out = ColorPrinter().print
	Arguments can be builtins, schemes, or integers:
		out('plain')
		out('this is angry i.e. red and bold','angry')
		out('this is just red','red')
		out('this message is ansi',91)
	"""
	#! systematic way to load this with all the colors?
	defs_colors = dict(
		red=91,purple=95,cyan=96,dark_cyan=36,blue=94,green=92,
		bold=1,underline=4,blink=5,gray=123,
		b_black=40)
	schemes = dict(angry=('red','bold'),
		red_black=('red','b_black'),cyan_black=('cyan','b_black'))
	def _syntax(self,text,how=None): 
		return b'\033[%sm%s\033[0m'%(
			';'.join([str(i) for i in how]) if how else '',
			text if not self.tag else '%s%s'%(self.tag,text))
	def __init__(self,scheme=None,tag=None,back=False):
		self.back = back
		self.scheme = scheme
		self.name_to_colors = dict((i,(j,)) for i,j in self.defs_colors.items())
		self.name_to_colors.update(**dict([(i,tuple([
			m for n in (self.name_to_colors[k] for k in j) for m in n]))
			for i,j in self.schemes.items()]))
		self.tag = tag
	def printer(self,text,*how,**kwargs):
		#! is it clumsy to do kwargs this way? slow
		back = kwargs.pop('back',self.back)
		if kwargs: raise Exception
		scheme = how if how else self.scheme
		if not scheme: this = text if not self.tag else '%s%s'%(self.tag,text)
		else: 
			spec = list(set([i for j in [
				self.name_to_colors.get(h,(h,)) for h in how] for i in j]))
			invalid_codes = [s for s in spec if not isinstance(s,int)]
			if any(invalid_codes): 
				raise Exception('Invalid ANSI codes: %s'%str(invalid_codes))
			this = self._syntax(text=text,how=spec)
		if back: return this
		else: print(this)

def ctext(*args,**kwargs):
	"""
	Wrap the color printer so you can get 
	color text back with ctext('error','angry').
	"""
	printer = ColorPrinter(back=True).printer
	return printer(*args,**kwargs)

def confirm(*msgs,**kwargs):
	"""Check with the user."""
	sure = kwargs.pop('sure',False)
	if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
	return sure or all(
		re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('[QUESTION] %s (y/N)? '%msg))!=None for msg in msgs)

class Hook(object):
	"""
	! document why hooks are great: seamless debugging, can override functions, etc
	"""
	def __init__(self,source,target):
		self.source = source
		self.target = target
		#! why can we not put this at the top of the script?
		from ortho import importer
		self._module = importer(self.source)
		self._function = self._module[target]
	@property
	def function(self):
		return self._function

def mkdirs(path):
	"""
	Equivalent of `mkdir -p` for making directories.
	"""
	# via https://stackoverflow.com/questions/600268
	# note that you must protect against tilde or you get non-symbolic links
	#   to home which depend on the mounting system and are difficult to 
	#   delete properly
	path_real = os.path.abspath(os.path.expanduser(path))
	try: os.makedirs(path_real)
	except OSError as exc:
		import errno
		if exc.errno == errno.EEXIST and os.path.isdir(path_real): pass
		else: raise

def status(string,i=0,loop=None,bar_character=None,width=None,spacer='.',
	bar_width=25,tag='status',start=None,pad=None,refresh=True,looplen=None):
	"""
	Show a status bar and counter for a fixed-length operation.
	Origin in automacs and adapted for python 2 and 3.
	"""
	#! possible bug below where "lines get shorter and garbage is left behind"
	if loop and looplen: 
		raise Exception('use either loop (%s) or looplen (%s)'%(loop,looplen))
	#! it would be useful to receive a signal here to suppress the status bar 
	#!  from printing to the log file on backrun
	# use unicode if not piping to a log file
	logfile = (not hasattr(sys.stdout,'isatty')) or sys.stdout.isatty()==False
	# use of equals sign below is deprecated when we 
	#   suppress status bars in the log file below
	if not logfile: 
		left,right,bb = u'\u2590',u'\u258C',(u'\u2592' if bar_character==None else bar_character)
	else: left,right,bb = '|','|','='
	string = '[%s] '%tag.upper()+string if tag != '' else string
	if width: string = string.ljust(width,spacer)[:width]
	if pad: string = ('%-'+str(int(pad))+'s')%string
	if not looplen:
		if not logfile: sys.stdout.write(string+'\n')
		else: sys.stdout.write(string+'\n')
	elif looplen and logfile and i==0: sys.stdout.write('[STATUS] running a loop ')
	# suppress progress bar in the log file except on the last item
	elif looplen and logfile and i>0 and i<looplen-1: sys.stdout.write('.')
	else:
		if start != None:
			esttime = (time.time()-start)/(float(i+1)/looplen)
			timestring = ' %s minutes'%str(abs(round((esttime-(time.time()-start))/60.,1)))
			bar_width = 15
		else: timestring = ''
		countstring = str(i+1)+'/'+str(looplen)
		bar = ' %s%s%s '%(left,int(bar_width*(i+1)/looplen)*bb+' '*\
			(bar_width-int(bar_width*(i+1)/looplen)),right)
		if not logfile: 
			output = (u'\r' if refresh else '')+string+bar+countstring+timestring+' '
			if sys.version_info<(3,0): output = output.encode('utf-8')
			if refresh:
				sys.stdout.flush()
				sys.stdout.write(output)
			else: print(output)
		else: 
			# suppressed progress bar in the logfile avoids using carriage return
			sys.stdout.write('[STATUSBAR] '+string+bar+countstring+timestring+' ')
		if i+1<looplen: sys.stdout.flush()
		else: sys.stdout.write('\n')

class Observer(object):
	"""
	Watch locals and return them. 
	The umpteenth metaprogramming trick for nice environments!
	via https://stackoverflow.com/questions/9186395
	"""
	def __init__(self,function):
		self._locals = {}
		self.function = function
	def __call__(self,*args,**kwargs):
		def tracer(frame,event,arg):
			if event=='return': 
				self._locals = frame.f_locals.copy()
				# it is unwise to modify locals so dynamic variables can drop to _locals
				self._locals.update(**self._locals.get('__locals__',{}))
		# tracer is activated on next call, return or exception
		sys.setprofile(tracer)
		# trace the function call
		try: res = self.function(*args,**kwargs)
		# disable tracer and replace with old one
		finally: sys.setprofile(None)
	def clear_locals(self): self._locals = {}
	@property
	def locals(self): return self._locals

def lowest_common_dict_denominator(data):
	"""Used by compare_dicts to compare dictionaries with strings vs unicode strings."""
	# possibly via: https://stackoverflow.com/questions/1254454/
	if isinstance(data,basestring): return str(data)
	elif isinstance(data,collections.Mapping): 
		return dict(map(lowest_common_dict_denominator,data.items()))
	elif isinstance(data,collections.Iterable): 
		return type(data)(map(lowest_common_dict_denominator,data))
	else: return data

def compare_dicts(a,b):
	"""Compare dictionaries with unicode strings."""
	#! used when you need strings to come out
	return lowest_common_dict_denominator(a)==lowest_common_dict_denominator(b)
