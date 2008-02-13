#!/usr/bin/env python
# encoding: utf-8
"""
whatever.py

Will's Hastily-Assembled Toolkit for Experimental Validation, Execution, and Recording

Software to manage experiments.  Runs experiments based on a configuration file 
or interactively-specified configuration and saves results to a database.  Can 
also post-process the database file to get results into LaTeX, spreadsheets, etc.

Requires Python 2.5; PyYAML recommended (tested with 3.0.5)

Created by Will Benton on 2008-02-11.
Copyright (c) 2008 Aition Technologies, LLC and Will Benton. All rights reserved.

$Id$
"""

import sys
import getopt
import zlib
import readline
from select import select
import subprocess
import StringIO

from sets import Set

from cmd import Cmd
import shlex

sqlite3 = None
yaml = None

class Task(object):
	"""docstring for Task"""
	DEVNULL = open('/dev/null', 'w') 
	STDOUT = "stdout"
	STDERR = "stderr"
	TIMINGS = "timings"
	NONE = "none"
	
	popen = subprocess.Popen
	
	FDS = [STDOUT, STDERR]
	
	def __getfile(self, nm):
		if self.fds.has_key(nm):
			return self.fds[nm]
		
		if self.keeplist.__contains__(nm):
			self.fds[nm] = subprocess.PIPE
			return self.fds[nm]
		
		return Task.DEVNULL
	
	def __init__(self, tid, exe):
		super(Task, self).__init__()
		self.tid = tid
		self.keeplist = Set()
		self.keeptime = False
		
		self.exe = exe
		self.input = None
		self.args = []
		
		self.out = None
		self.err = None
		
		self.fds = dict()
	
	def keep(self, name):
		if Task.FDS.__contains__(name):
			self.keeplist.add(name)
			return
			
		if name == Task.TIMINGS:
			self.keeptime = True
			return
		
		if name == Task.NONE:
			self.keeptime = False
			self.keeplist.clear()
	
	def setargs(self, args):
		self.args = args
	
	def setinput(self, input):
		"""
		Sets the input for this task.
		"""
		self.input = input
	
	def get(self, stream):
		if self.fds.has_key(stream):
			return self.fds[stream]
		else:
			return None
	
	def run(self, env=None):
		"""
		Expands any variables in the command-line arguments and runs this task, blocking until it is complete.
		Note:  variable expansion not enabled yet.
		"""
		
		from cStringIO import StringIO
		
		# fixme : make this into a zlib-backed sink
		make_sink = lambda: StringIO()
		
		try:
			out = self.__getfile(Task.STDOUT)
			err = self.__getfile(Task.STDERR)
			# FIXME:  expand variables
			cmdline = [self.exe]
			if self.args is not None:
				cmdline.extend(self.args)
			proc = Task.popen(cmdline, stdin=self.input, stdout=out, stderr=err, close_fds=True)
			
			# file descriptors to watch
			towatch = map(lambda fd: getattr(proc, fd), self.keeplist)
			sinks = { proc.stdout : make_sink(), proc.stderr : make_sink() }
			done = False
			
			if(len(towatch) > 0):
				while proc.poll() is None or not done:
					bytes_read = 0
					(_ignore, ready, _ignore) = select([],towatch,[])
					to_store = map(lambda f: (sinks[f], f.read(64)), ready)
					for location, data in to_store:
						bytes_read += len(data)
						location.write(data)
					done = bytes_read == 0
				
				self.out = sinks[proc.stdout].getvalue()
				self.err = sinks[proc.stderr].getvalue()
			else:
				ret = proc.wait()
		except OSError, err:
			print "failed to exec %s because of %s" % (self.exe, err)
		
class Config(object):
	"""An experiment configuration"""
	
	PRE = "pre"
	POST = "post"
	
	def __mk_subconf(self, scname):
		""" 
		makes a new subconfiguration with name scname, adds 
		it to this configuration's list of subconfigurations 
		"""
		sc = dict()
		sc[PRE] = list()
		sc[POST] = list()
		self.subconfs[scname] = sc
		return sc
		
	def __init__(self, name):
		super(Config, self).__init__()
		self.nm = name
		self.subconfs = dict()
		self.tasks = list()
	
	def name(self):
		return self.nm

class ExpInterpreter(Cmd):
	"""
	This class implements a command-line interpreter for experiment configurations.
	"""
	helpmsg = """
Commands include:

notebook <filename>

declare <configname>

pre {<subconfname>, DEFAULT} <exe>
post {<subconfname>, DEFAULT} <exe>

task <task_id> <exe>
keep {out, err, timings, none} for <task_id>

datapoint <datapoint_name> is {string, int, float}
watch <task_id> for <datapoint_name> as <regexp>

global <var> := <value>
local <input_id> <var> := <value>

name <input_id> <fancy_name>
args <input_id> <task_id> <arg_1> [...]
input <input_id> <task_id> <filename>

show {"pre", "post", "task", "all"}

iterations <n>

end

run [<configname>] {"all", <id>}

load <filename>
save <filename>

Type "help commandname" for more information on a given command, 
"help globals" for more information on built-in global variables, or
"help locals" for more information on built-in local variables.
"""
	
	def basic_prompt(self):
		return "  > "
	
	def config_prompt(self, name):
		return " %s > " % str(name)
	
	def __ni(self, s):
		print "sorry, %s is not implemented" % s
		
	def __check_for_yaml(self, s):
		if yaml is None:
			print "%s requires PyYAML to be installed"
			return False
		else:
			return True
	
	def __lexargs(self, arg):
		try:
			return shlex.split(arg)
		except ValueError, err:
			print "Invalid syntax:  \"%s\"" % arg
			return None
	
	def __init_subconf(self, name):
		v = dict()
		v["name"] = name
		v["pre"] = list()
		v["post"] = list()
		subs = self.current["SUB"]
		subs[name] = v
	
	def __init_config(self, name):
		self.current = dict()
		self.current["SUB"] = dict()
		self.current["name"] = name
	
	def __init__(self):
		Cmd.__init__(self)
		self.prompt = self.basic_prompt()
		self.configurations = dict()
		self.in_config = False
		
	def do_declare(self, arg):
		args = self.__lexargs(arg)
		
		if self.in_config:
			print "Error:  currently declaring configuration %s; please finish declaration with 'end' first" % self.current["name"]
			return
		if len(args) > 1:
			print "Invalid syntax '%s' (too many args; \"help declare\" for more info.)" % arg
			return
		
		if self.configurations.has_key(arg):
			print "Configuration name '%s' is already declared; please choose another" % arg
			return
		
		self.in_config = True
		self.__init_config(args[0])
		self.prompt = self.config_prompt(args[0])
		print "Defining trials for configuration %s" % arg
	
	def do_end(self, arg):
		if not self.in_config:
			print "Error:  nothing to end here; please declare a configuration first"
			return
		self.in_config = False
		name = self.current["name"]
		self.configurations[name] = self.current
		self.current = None
		self.prompt = self.basic_prompt()
	
	def do_pre(self, arg):
		pass
		
	def do_post(self, arg):
		pass
	
	def do_EOF(self, arg):
		sys.exit(0)
	
	def help_declare(self):
		print "syntax:  declare <configname>"
		print "  Indicates that you are declaring a new experiment configuration."
		print "  You must do this before executing any other commands."
	
	def help_globals(self):
		self.__ni("help for globals")
	
	def help_locals(self):
		self.__ni("help for locals")
		
	def do_help(self, arg):
		print self.helpmsg

help_message = '''
The help message goes here.
'''

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

def init():
	"""Loads sqlite3 and Yaml libraries"""
	global sqlite3
	global yaml
	
	try:
		sqlite3 = __import__('sqlite3')
	except ImportError:
		raise Usage("whatever requires python 2.5")
	
	try:
		yaml = __import__('yaml')
	except ImportError:
		print "PyYAML is recommended, but I can't find it.  Will run without it; load and save of configurations will be disabled"

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
