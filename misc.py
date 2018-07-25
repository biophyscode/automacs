#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
import os,sys,re,json

# adjucate string types between versions
str_types = [str,unicode] if sys.version_info<(3,0) else [str]

def listify(x): 
	"""Turn a string or a list into a list."""
	if type(x)==str: return [x]
	elif type(x)==list: return x
	else: raise Exception('listify expects a string or a list')

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
	if type(obj) in [float,int,bool]+str_types:
		if depth == 0: print(spacer+str(obj)+'\n'+horizo*len(obj))
		else: print(spacer+str(obj))
	elif type(obj) == dict and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) in [list,tuple]:
		for ind,item in enumerate(obj):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(item) in [float,int,bool]+str_types: print(spacer_this+str(item))
			elif item != {}:
				print(spacer_this+'('+str(ind)+')')
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print('unhandled tree object %s'%item)
	elif type(obj) == dict and obj != {}:
		for ind,key in enumerate(obj.keys()):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(obj[key]) in [float,int,bool]+str_types: print(spacer_this+key+' = '+str(obj[key]))
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
				else: print(spacer_this+key)
				asciitree(obj[key],depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			elif type(obj[key])==list and obj[key]==[]:
				print(spacer_this+'(empty)')
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
	# use case insensitive grep with the -i flag below
	os.system(r'find ./ -name "*.py" | xargs egrep -i --color=always "(def|class) \w*%s\w*"'%keyword)
