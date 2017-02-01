#!/usr/bin/env python

import sys,subprocess

_not_reported = ['status']

def status(string,i=0,looplen=None,bar_character=None,width=25,tag='',start=None):
	"""
	Show a status bar and counter for a fixed-length operation.
	"""
	#---! it would be useful to receive a signal here to suppress the status bar from 
	#---! ...printing to the log file on backrun.
	#---use unicode if not piping to a log file
	logfile = sys.stdout.isatty()==False
	#---use of equals sign below is deprecated when we suppress status bars in the log file below
	if not logfile: 
		left,right,bb = u'\u2590',u'\u258C',(u'\u2592' if bar_character==None else bar_character)
	else: left,right,bb = '|','|','='
	string = '[%s] '%tag.upper()+string if tag != '' else string
	if not looplen:
		if not logfile: sys.stdout.write(string)
		else: sys.stdout.write(string+'\n')
	#---suppress progress bar in the log file except on the last item
	elif looplen and logfile and i < looplen-1: pass
	else:
		if start != None:
			esttime = (time.time()-start)/(float(i+1)/looplen)
			timestring = ' %s minutes'%str(abs(round((esttime-(time.time()-start))/60.,1)))
			width = 15
		else: timestring = ''
		countstring = str(i+1)+'/'+str(looplen)
		bar = ' %s%s%s '%(left,int(width*(i+1)/looplen)*bb+' '*(width-int(width*(i+1)/looplen)),right)
		if not logfile: 
			output = u'\r '+string+bar+countstring+timestring+' '
			if sys.version_info<(3,0): output = output.encode('utf-8')
			sys.stdout.flush()
			sys.stdout.write(output)
		else: 
			#---suppressed progress bar in the logfile avoids using carriage return
			sys.stdout.write('[STATUSBAR] '+string+bar+countstring+timestring+' ')
		if i+1<looplen: sys.stdout.flush()
		else: sys.stdout.write('\n')

def bash(command,log=None,cwd=None,inpipe=None):

	"""
	Run a bash command
	"""
	
	if not cwd: cwd = './'
	if log == None: 
		if inpipe: raise Exception('under development')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		proc = subprocess.Popen(command,**kwargs)
		stdout,stderr = proc.communicate()
	else:
		output = open(cwd+'log-'+log,'w')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		if inpipe: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if not inpipe: stdout,stderr = proc.communicate()
		else: stdout,stderr = proc.communicate(input=inpipe)
	if stderr: raise Exception('[ERROR] bash returned error state: %s'%stderr)
