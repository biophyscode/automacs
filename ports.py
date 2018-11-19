#!/usr/bin/env python

def check_port(port,strict=False):
	"""
	Check if a port is available.
	"""
	free = True
	import socket
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	try: s.bind(("127.0.0.1",port))
	except socket.error as e: 
		free = False
		if strict: raise Exception('port %d is not free: %s'%(port,str(e)))
		else: raise Exception('port %d is occupied'%port)
	s.close()
	return free
