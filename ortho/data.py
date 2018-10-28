#!/usr/bin/env python

from __future__ import print_function
import json,re
from .misc import str_types

# check keys via check_repeated_keys function below

#! dotdict!
# explicit error message for dictionary failures
msg_no_key = 'this DotDict "%s" cannot find a key you have requested: "%s". '+\
	'this typically happens for one of the following reasons. (1) you forgot to include a key in the '+\
	'settings block of your experiment. (2) the settings block for your experiment (or a run it uses) '+\
	'has a syntax error or repeated keys. if this happens, scroll up to see a warning '+\
	'("settings was broken") to troubleshoot the error. (3) in rare cases a control flow problem in an '+\
	'automacs library may not correctly put the right data into the state.'

def jsonify(text): 
	"""
	Convert python to JSON by replacing single quotes with double quotes and stripping trailing commas
	Note that this checker might be oversensitive if additional JSON errors with the nested dictionary
	Used before SafeDictHook to check for redundant keys. We use a placeholder in block text because JSON 
	cannot process it and the point of this function is to use SafeDictHook to prevent redundant keys.
	"""
	# remove comments because they might corrupt the JSON
	re_block_comments = re.compile(r'([\"]{3}.*?[\"]{3})',flags=re.M+re.DOTALL)
	text = re_block_comments.sub('"REMOVED_BLOCK_COMMENT"',text)
	# note that this fails if you use hashes inside of dictionary values
	re_comments = re.compile(r'(#.*?)\n',flags=re.M+re.DOTALL)
	text = re_comments.sub('',text)
	# strip trailing commas because they violate JSON rules
	text = re.sub(r",[ \t\r\n]*([}\]])",r"\1",text.replace("'","\""))
	# fix the case on all booleans
	text = re.sub("True","true",text)
	text = re.sub("False","false",text)
	text = re.sub("None","null",text)
	# remove whitespace
	re_whitespace = re.compile(r'\n\s*\n',flags=re.M)
	text = re_whitespace.sub('\n',text)
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
		# if we get a type error we are probably on python < 2.7
		# ... where json lacks the hook so we just give a warning and pass
		if type(e)==TypeError:
			print('warning','JSON encountered a type error which suggests an old version '
				'(possibly python 2.6) so we will pass. beware repeated keys or downstream '
				'dictionary errors')
			return True
		print('error','found repeated keys (or JSON encoding error). '+extra_msg)
		if verbose: 
			text_with_linenos = '\n'.join(['[DEBUG]%s|%s'%(str(ll).rjust(4),l) 
				for ll,l in enumerate(text_json.splitlines())])
			print('warning','the following string has a JSON problem:\n'+text_with_linenos)
			print('exception','exception is %s'%e)
			print('note',controlmsg['json'])
		return False
	return True

#!!! need a yaml repeated key checker because this is not native

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
	elif len(k)==1: 
		try: o[k[0]] = value
		except:
			import pdb;pdb.set_trace()
	else:
		if k[0] not in o: o[k[0]] = {}
		delveset(o[k[0]],*k[1:],value=value)

def dictsub(subset,superset): 
	"""See if one dictionary is contained in another."""
	return all(item in superset.items() for item in subset.items())

def dictsub_strict(subset,superset): 
	"""See if one dictionary is contained in another."""
	return all(item in superset.items() for item in subset.items())

def dictsub_sparse(small,big): 
	"""See if the routes in one dictionary are contained in another (hence less strict than dictsub)."""
	return all([(r,v) in catalog(big) for r,v in catalog(small)])

def json_type_fixer(series):
	"""Cast integer strings as integers, recursively. We also fix 'None'."""
	for k,v in series.items():
		if type(v) == dict: json_type_fixer(v)
		elif type(v)in str_types and v.isdigit(): series[k] = int(v)
		elif type(v)in str_types and v=='None': series[k] = None

def catalog(base,path=None):
	"""
	Traverse all paths in a nested dictionary. Returns a list of pairs: paths and values.
	Note that lists can be a child item; catalog does not expand the indices.
	"""
	#! should this return a tuple as the path in case it gets routed to delve?
	if not path: path = []
	if isinstance(base,dict):
		for x in base.keys():
			local_path = path[:]+[x]
			for b in catalog(base[x],local_path): yield b
	else: yield path,base

def unique_ordered(seq):
	"""Return unique items maintaining the order."""
	vals = set()
	return [x for x in seq if not (x in vals or vals.add(x))]
