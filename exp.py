#!/usr/bin/env python
# encoding: utf-8
"""
exp.py

Software to manage experiments.  Runs experiments based on a configuration file 
and saves results to a database.  Can also post-process the configuration file to get
results into LaTeX, spreadsheets, etc.

Created by Will Benton on 2008-02-11.
Copyright (c) 2008 Aition Technologies, LLC and Will Benton. All rights reserved.

$Id:$
"""

import sys
import getopt


help_message = '''
The help message goes here.
'''


class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


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
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2


if __name__ == "__main__":
	sys.exit(main())
