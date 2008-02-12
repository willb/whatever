#!/usr/bin/env python
# encoding: utf-8
"""
whatever.py

Will's Hastily-Assembled Toolkit for Experimental Validation, Execution, and Recording

Software to manage experiments.  Runs experiments based on a configuration file 
and saves results to a database.  Can also post-process the database file to get
results into LaTeX, spreadsheets, etc.

Created by Will Benton on 2008-02-11.
Copyright (c) 2008 Aition Technologies, LLC and Will Benton. All rights reserved.

$Id$
"""

import sys
import getopt
import zlib
import readline
import select
import subprocess
import yaml

from cmd import Cmd

sqlite3 = None

class ExpInterpreter(Cmd):
	"""
	This class implements a command-line interpreter for experiment configuration.
	"""
	helpmsg = """
Commands include:

define <configname>

pre {<subconfname>, "all"} <exe>
post {<subconfname>, "all"} <exe>
task {<subconfname>, "all"} <n> <exe>

keep {"out", "err", "none"}

iterations <n>

input <id> {"args", "file"} ...
trial {<subconfname>, "all"} <exe>

Type "help commandname" for more information on a given command.
	"""
	
	config = dict()
	
	def __init__(self):
		Cmd.__init__(self)
		self.prompt = "  > "
		
	def do_define(self, arg):
		if len(arg.split()) > 1:
			print "Configuration name '%s' is invalid; must not contain whitespace" % arg
			return
		self.confname = arg
		self.prompt = "  %s > " % arg
		print "Defining trials for configuration %s" % arg
	
	def do_EOF(self, arg):
		sys.exit(0)
	
	def do_help(self, arg):
		print self.helpmsg

help_message = '''
The help message goes here.
'''

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

def init():
	""" Loads sqlite3 library  """
	global sqlite3
	try:
		sqlite3 = __import__('sqlite3')
	except ImportError:
		raise Usage("This requires python 2.5")

def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "ho:v", ["help", "output="])
		except getopt.error, msg:
			raise Usage(msg)
	
		# option processing
		for option, value in opts:
			if option == "-v":
				verbose = True
			if option in ("-h", "--help"):
				raise Usage(help_message)
			if option in ("-o", "--output"):
				output = value
		
		init()
		interpreter = ExpInterpreter()
		interpreter.cmdloop()
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2


if __name__ == "__main__":
	sys.exit(main())
