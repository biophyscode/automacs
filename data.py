#!/usr/bin/env python

from __future__ import print_function
import json,re

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
	re_whitespace = re.compile('\n\s*\n',flags=re.M)
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
