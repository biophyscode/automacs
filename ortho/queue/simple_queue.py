#!/usr/bin/env python

import os,stat
import ortho

def simple_task_queue(**kwargs):
	"""
	A minimal task queue.
	"""
	lock_file = kwargs.pop('lock','LOCK.lockness.sh')
	log_file = kwargs.pop('log','screenlog')
	# hook for flock which installs it if necessary on macos
	flock_bin = ortho.config_hook_get('flock1','flock')
	ortho.bash(('FLOCK_CMD=%s SCREEN_LOG_QUEUE=%s LOCK_FILE=%s '
		'bash ortho/queue/lockness.sh')%
		(flock_bin,log_file,lock_file),announce=True)
	print('status task queue is running!')
	#! need a lock file and a log file
	return {'lock':lock_file,'log':log_file}

def launch(*args,**kwargs):
	"""Run something in the task queue. A trivial wrapper."""
	cwd = kwargs.pop('cwd',None)
	command = kwargs.pop('command',None)
	#! cannot be a BASH-interpretable command here?
	queue_fn = ortho.conf.get('task_queue','TASK_QUEUE')
	try: os.stat(queue_fn)
	except: raise Exception('cannot find a task queue at %s'%queue_fn)
	if not stat.S_ISFIFO(os.stat(queue_fn).st_mode):
		raise Exception('cannot confirm %s is a fifo'%queue_fn)
	form_args = ' '.join(args) if args else ''
	form_kwargs = ('' if not kwargs else 
		' '.join(['%s="%s"'%(i,j) for i,j in kwargs.items()]))
	# using the command kwarg triggers an explicit mode
	if command and (args or kwargs):
		raise Exception(
			'cannot mix command with other arguments: %s and %s'%(args,kwargs))
	if not command:
		command = ' '.join([i for i in ['make',form_args,form_kwargs] if i])
	if cwd: command = 'cd %s && %s'%(cwd,command)
	ortho.bash('echo "%s" > %s'%(command,queue_fn),announce=True)

"""
unfinished business:
	logs of the queue?
		jobs started
		jobs completed
		difference is the number in the queue
	cleanup when queue fails
"""

