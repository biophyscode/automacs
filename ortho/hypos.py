#!/usr/bin/env python

import copy
from .data import delve

def hypothesis(sweep,default=None):
	"""
	Code for sweeping an arbitrarily deep dictionary over many dimensions in combinations.
	Adapted from hypothesize so that no default is necessary. Only changed the name slightly for readability.
	"""
	# create the default hypothesis
	if default==None: default = {}
	for pathway in sweep:
		if pathway['route'][0] not in default: default[pathway['route'][0]] = {}
		for i in range(1,len(pathway['route'])-1):
			level = delve(default,*pathway['route'][:i])
			if pathway['route'][i] not in level: level[pathway['route'][i]] = {}
		if len(pathway['route'])>1: 
			delve(default,*pathway['route'][:-1])[pathway['route'][-1]] = list(pathway['values'])[0]
	for i in default: default[i] = None if default[i] == {} else default[i]

	# extract a list of lists of parameters to sweep over
	t = [i['values'] for i in sweep]
	# note that this non-numpythonic way of doing this has not been rigorously tested
	# note that the previous meshgrid method did not work on all types
	allcombos = list([[i] for i in t[0]])
	for s in t[1:]:
		for bi in range(len(allcombos)):
			b = allcombos.pop(0)
			for r in list(s): allcombos.append(b + [r])

	# assemble a list of hypotheses from all possible combinations of the sweep values
	# note that this code is general, and works for an arbitrarily deep dictionary
	hypotheses = []
	# for each combo generate a new hypothesis
	for combo in allcombos:
		# start with the default hypothesis
		newhypo = copy.deepcopy(default)
		# each combo has a value and a route which is a sequence of dictionary keys
		#   we loop over each route to set each final value for the sweep
		for routenum in range(len(sweep)):
			# to get to the deepest part of that route we use tmp as a pointer
			#   and iteratively traverse one level until the second to last level
			tmp = newhypo[sweep[routenum]['route'][0]]
			# the following checks if we are already at the end of the dictionary 
			if type(newhypo[sweep[routenum]['route'][0]]) != dict:
				newhypo[sweep[routenum]['route'][0]] = combo[routenum]
			else:
				for i in sweep[routenum]['route'][1:-1]: tmp = tmp[i]
				# at the final level, we now have a pointer to the lowest dictionary to set the value
				tmp[sweep[routenum]['route'][-1]] = combo[routenum]
		# once we set all the values, the hypothesis is ready
		hypotheses.append(newhypo)	
	return hypotheses

def sweeper(**kwargs):
	"""
	A simple method for sweeping many parameters. Provides a simple interface to the hypothesis function
	but does not allow arbitrary nested dictionaries. Instead of supplying explicit routes and values, the
	keys in kwargs are the routes (hence only one is possible).
	"""
	return hypothesis([dict(route=[key],values=val) for key,val in kwargs.items()])
