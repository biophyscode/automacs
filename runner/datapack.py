#!/usr/bin/env python

"""
DATAPACK

Tools for manipulating data structures in ACME. 

These functions provide a number of useful features for ACME, but they can also be imported individually even
if you don't import the whole module (see the vmd module for an example of this -- it uses the DotDict, among)
other things. The DotDict enables us to use attribute-style lookups on dictionaries, and also provides a 
method which checks the ``settings`` dictionary for values not found in the ``state`` dictionary (both are 
shared in the global namespace). We also provide a ``jsonify`` function that checks python dictionary literals
found in e.g. an experiment file for repeated keys so users don't redefine important variables. The ``yamlb``
function processes all incoming experiment settings into a nested dictionary which is loaded into the shared
``settings``variable.
"""

import os,sys,re,json

#---import magic
sys.path.insert(0,os.path.dirname(os.path.relpath(os.path.abspath(__file__),os.getcwd())))
from controlspec import controlspec,controlmsg
#from acme import get_path_to_module

#---release some functions for external import 
#---...but then hide them from the function which parses the command-line for targets
__all__ = ['DotDict','yamlb']
_not_all = ['DotDict','yamlb']

#---explicit error message for dictionary failures
msg_no_key = 'this DotDict "%s" cannot find a key you have requested: "%s". '+\
	'this typically happens for one of the following reasons. (1) you forgot to include a key in the '+\
	'settings block of your experiment. (2) the settings block for your experiment (or a run it uses) '+\
	'has a syntax error or repeated keys. if this happens, scroll up to see a warning '+\
	'("settings was broken") to troubleshoot the error. (3) in rare cases a control flow problem in an '+\
	'automacs library may not correctly put the right data into the state.'

class DotDict(dict):
	"""
	Use dots to access dictionary items.
	"""
	def __init__(self,*args,**kwargs):
		#---special sauce that maps the dictionary self to its own attributes list
		self.__dict__ = self
		#---maintain a list of protected keywords used by the dict object
		self.__dict__['_protect'] = list(dict.__dict__.keys())
		#---load the dictionary with incoming args and kwargs
		for key,val in args: self.__dict__[key] = val
		self.update(kwargs)
	def __setattr__(self,key,val):
		if key in self.get('_protect',[]): 
			raise Exception('cannot use dict/protected attribute %s'%key)
		#---special sauce that allows you to set new attributes
		super(dict,self).__setattr__(key,val)
	def __repr__(self): 
		#---hide the underscore attributes
		return str(dict([(i,j) for i,j in self.items() if not i.startswith('_')]))
	def __getattr__(self,key):
		"""
		The previous code is sufficient for a standard DotDict.
		The following allows fallback lookups.
		Development note: add protection that asserts that the query function q is callable
		Note that attribute lookups here throw an error if no match (because there is no default),
		hence you should use the query function directly for "get" (with default) functionality.
		"""
		if key in self: return self[key]
		#---failed attributes are looked up with the query function if available
		#---note that the q function can be permissive and return None on key failures
		elif 'q' in self: return self.q(key)
		else: 
			#---it would be nice to get the name of the variable for self but this is very difficult
			#---...and the user should be able to do a traceback with the ample error messages
			#---we addded the verbose message because we were not scrolling up to note JSON errors
			raise Exception(msg_no_key%(id(self),key))

def jsonify(text): 
	"""
	Convert python to JSON by replacing single quotes with double quotes and stripping trailing commas
	Note that this checker might be oversensitive if additional JSON errors with the nested dictionary
	Used before SafeDictHook to check for redundant keys. We use a placeholder in block text because JSON 
	cannot process it and the point of this function is to use SafeDictHook to prevent redundant keys.
	"""
	#---remove comments because they might screw up the JSON
	text = re.sub(r'([\"]{3}.*?[\"]{3})','"REMOVED_BLOCK_COMMENT"',text,flags=re.M+re.DOTALL)
	#---note that this fails if you use hashes inside of dictionary values
	text = re.sub(r'(#.*?)\n','',text,flags=re.M+re.DOTALL)
	#---strip trailing commas because they violate JSON rules
	text = re.sub(r",[ \t\r\n]*([}\]])",r"\1",text.replace("'","\""))
	#---fix the case on all booleans
	text = re.sub("True","true",text)
	text = re.sub("False","false",text)
	text = re.sub("None","null",text)
	text = re.sub('\n\s*\n','\n',text,re.M)
	#---! rpb is worried that this is a hack
	return text

class SafeDictHook(dict):
	"""
	Hook for json.loads object_pairs_hook to catch repeated keys.
	"""
	def __init__(self,*args,**kwargs):
		self.__class__ == dict
		if len(args)>1: raise Exception('development failure')
		keys = [i[0] for i in args[0]]
		if len(keys)!=len(set(keys)): 
			raise Exception(controlmsg['json']+' PROBLEM KEYS MIGHT BE: %s'%str(keys))
		self.update(*args,**kwargs)

def check_repeated_keys(text,verbose=False):
	"""
	Confirm that dict literals pass through non-redundant json checker.
	"""
	extra_msg = "either fix the repeated keys or check for JSON problems."
	text_json = jsonify(text)
	try: _ = json.loads(text_json,object_pairs_hook=SafeDictHook)
	except Exception as e: 
		print('[ERROR] found repeated keys (or JSON encoding error). '+extra_msg)
		if verbose: 
			text_with_linenos = '\n'.join(['[DEBUG]%s|%s'%(str(ll).rjust(4),l) 
				for ll,l in enumerate(text_json.splitlines())])
			print('[ERROR] the following string has a JSON problem:\n'+text_with_linenos)
			print('[ERROR] exception is %s'%e)
			print('[NOTE] '+controlmsg['json'])
		return False
	return True

def catalog(base,path=None):
	"""
	Traverse all paths in a nested dictionary. Returns a list of pairs: paths and values.
	Note that lists can be a child item; catalog does not expand the indices.
	"""
	if not path: path=[]
	if isinstance(base,dict):
		for x in base.keys():
			local_path = path[:]+[x]
			for b in catalog(base[x],local_path): yield b
	else: yield path,base

def yamlb(text,style=None,ignore_json=False):
	"""
	Basic parser which reads elegantly-formatted settings blocks (in a manner similar to YAML).
	Development note: missing colons are hard to troubleshoot. Predict them?
	Development note: doesn't prevent errors with multiple keys in a dictionary!
	"""
	unpacked,compacts = {},{}
	str_types = [str,unicode] if sys.version_info<(3,0) else [str]
	#---evaluate code blocks first
	regex_block_standard = r"^\s*([^\n]*?)\s*(?:\s*:\s*\|)\s*([^\n]*?)\n(\s+)(.*?)\n(?!\3)"
	regex_block_tabbed = r"^\s*([^\n]*?)\s*(?:\s*:\s*\|)\s*\n(.*?)\n(?!\t)"
	if style == 'tabbed': regex_block = regex_block_tabbed
	else: regex_block = regex_block_standard
	regex_line = r"^\s*(.*?)\s*(?:\s*:\s*)\s*(.+)$"
	#---strip comments first 
	text = re.sub("\s*#.*?$",'',text,flags=re.M)
	while True:
		blockoff = re.search(regex_block,text,re.M+re.DOTALL)
		if not blockoff: break
		if style == 'tabbed': key,block = blockoff.groups()[:2]
		else: 
			#---collect the key, indentation for replacement, and value
			key,indent,block = blockoff.group(1),blockoff.group(3),''.join(blockoff.groups()[1:])
		#---alternate style does multiline blocks with a single tab character
		#---! who uses this? only vmdmake? might be worth dropping
		if style == 'tabbed': compact = re.sub("(\n\t)",r'\n',block.lstrip('\t'),re.M)
		#---remove indentations and newlines (default)
		else: compact = re.sub('\n','',re.sub(indent,'',block))
		key_under = re.sub(' ','_',key)
		if key_under in unpacked and not ignore_json:
			raise Exception('\n[ERROR] key is repeated in the settings: "%s"'%key)
		unpacked[key_under] = compact
		#---remove the block
		text,count = re.subn(re.escape(text[slice(*blockoff.span())]),'',text)
		if not ignore_json and count>1:
			raise Exception('\n[ERROR] key is repeated in the settings: "%s"'%key)
	while True:
		line = re.search(regex_line,text,re.M)
		if not line: break
		key,val = line.groups()
		key_under = re.sub(' ','_',key)
		if key_under in unpacked and not ignore_json:
			raise Exception('\n[ERROR] key is repeated in the settings: "%s"'%key)
		unpacked[key_under] = val
		text,count = re.subn(re.escape(text[slice(*line.span())]),'',text)
		if not ignore_json and count>1:
			raise Exception('\n[ERROR] key is repeated in the settings: "%s"'%key)
	#---evaluate rules to process the results
	for key,val_raw in unpacked.items():
		#---store according to evaluation rules
		try: val = eval(val_raw)
		except SyntaxError as e:
			#---use of the explicit dict constructor catches repeated keywords
			if e.msg=='keyword argument repeated': 
				raise Exception('keyword argument repeated in: "%s"'%val_raw)
			else: val = val_raw
		except: val = val_raw
		#---protect against sending e.g. "all" as a string and evaluating to builtin all function
		if val.__class__.__name__=='builtin_function_or_method': result = str(val_raw)
		elif type(val)==list: result = val
		elif type(val)==dict:
			if not ignore_json and not check_repeated_keys(val_raw):
				raise Exception(controlmsg['json']+' problem was found in: "%s"'%val_raw)
			result = val
		elif type(val) in str_types:
			if re.match('^(T|t)rue$',val): result = True
			elif re.match('^(F|f)alse$',val): result = False
			elif re.match('^(N|n)one$',val): result = None
			#---! may be redundant with the eval command above
			elif re.match('^[0-9]+$',val): result = int(val)
			elif re.match('^[0-9]*\.[0-9]*$',val): result = float(val)
			else: result = val
		else: result = val
		unpacked[key] = result
	if False:
		#---unpack all leafs in the tree, see if any use pathfinder syntax, and replace the paths
		ununpacked = [(i,j) for i,j in catalog(unpacked) if type(j)==str and re.match('^@',j)]
		for route,value in ununpacked:
			#---imports are circular so we put this here
			new_value = get_path_to_module(value)
			delveset(unpacked,*route,value=new_value)
	return unpacked

def delve(o,*k): 
	"""
	Return items from a nested dict.
	"""
	return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

def delveset(o,*k,**kwargs): 
	"""
	Utility function for adding a path to a nested dict.
	"""
	value = kwargs.pop('value',None)
	if value==None: raise Exception('delveset needs a value')
	if kwargs: raise Exception('unprocessed kwargs %s'%str(kwargs))
	if len(k)==0: raise Exception('deepset needs a path')
	elif len(k)==1: o[k[0]] = value
	else:
		if k[0] not in o: o[k[0]] = {}
		delveset(o[k[0]],*k[1:],value=value)

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
	if sys.version_info<(3,0): 
		corner,corner_end,horizo,horizo_bold,vertic,vertic_bold,tl,tr,bl,br = [i.encode('utf-8')
			for i in [corner,corner_end,horizo,horizo_bold,vertic,vertic_bold,tl,tr,bl,br]]
	spacer_both = dict([(k,{0:'\n',
		1:' '*(wide+1)*(depth-1)+c+horizo*wide,
		2:' '*(wide+1)*(depth-1)
		}[depth] if depth <= 1 else (
		''.join([(vertic if d not in last else ' ')+' '*wide for d in range(1,depth)])
		)+c+horizo*wide) for (k,c) in [('mid',corner),('end',corner_end)]])
	spacer = spacer_both['mid']
	if type(obj) in [str,float,int,bool]:
		if depth == 0: print(spacer+str(obj)+'\n'+horizo*len(obj))
		else: print(spacer+str(obj))
	elif type(obj) == dict and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) in [list,tuple]:
		for ind,item in enumerate(obj):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(item) in [str,float,int,bool]: print(spacer_this+str(item))
			elif item != {}:
				print(spacer_this+'('+str(ind)+')')
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print('unhandled tree object')
	elif type(obj) == dict and obj != {}:
		for ind,key in enumerate(obj.keys()):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(obj[key]) in [str,float,int,bool]: print(spacer_this+key+' = '+str(obj[key]))
			#---special: print single-item lists of strings on the same line as the key
			elif type(obj[key])==list and len(obj[key])==1 and type(obj[key][0]) in [str,float,int,bool]:
				print(spacer_this+key+' = '+str(obj[key]))
			#---special: skip lists if blank dictionaries
			elif type(obj[key])==list and all([i=={} for i in obj[key]]):
				print(spacer_this+key+' = (empty)')
			elif obj[key] != {}:
				#---fancy border for top level
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
			else: print('unhandled tree object')
	else: print('unhandled tree object')
	if not recursed: print('\n')
