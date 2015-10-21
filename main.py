#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import errno
import time

from jinja2 import Environment, FileSystemLoader

import tornado.ioloop
import tornado.web

from run import GSRun
from handlers import *

class GOPCAServer(object):
	def __init__(self,config=None):

		if config is None:
			config = self.get_config_from_cmdline()

		self.config = config

		# make sure run directory exists
		self.make_sure_path_exists(self.run_dir)

		self.template_loader = FileSystemLoader(searchpath = self.template_dir)
		self.template_env = Environment(loader = self.template_loader )

		self.runs = self.find_runs()
		print self.runs
		data = {'runs': self.runs, 'config': self.config, \
				'template_loader': self.template_loader, \
				'template_env': self.template_env}

		self.app = tornado.web.Application([
			(r'/static/(.*)$', tornado.web.StaticFileHandler, {'path': self.static_dir}),
			(r'/submit$', SubmitHandler,dict(data=data),'submit'),
			(r'/run/(.*)$', RunHandler,dict(data=data),'run'),
			(r'/(.*)$', MainHandler,dict(data=data),'main'),
		], cookie_secret=self.cookie_key)

	@property
	def port(self):
		return self.config['port']

	@property
	def run_dir(self):
		return self.config['run_dir']

	@property
	def static_dir(self):
		return self.config['static_dir']

	@property
	def template_dir(self):
		return self.config['template_dir']

	@property
	def disk_quota(self):
		return self.config['disk_quota']

	@property
	def max_file_size(self):
		return sef.config['max_file_size']

	@property
	def cookie_key(self):
		return self.config['cookie_key']

	@staticmethod
	def get_argument_parser():
		parser = argparse.ArgumentParser(description='GO-PCA web server')
		parser.add_argument('-k','--cookie-key',required=True,help='Secret cookie key')
		parser.add_argument('-p','--port',type=int,default=8080,help='Port that the server listens on')
		parser.add_argument('-r','--run-dir',default='runs',help='Directory for storing runs')
		parser.add_argument('-q','--disk-quota',type=float,default=5000.0,help='Maximal disk space to use, in MB')
		parser.add_argument('-s','--max-file-size',type=float,default=500.0,help='Maximal GO-PCA input size, in MB')
		parser.add_argument('--template-dir',default='templates',help='Jinja2 template directory')
		parser.add_argument('--static-dir',default='static',help='Directory for static content')
		return parser

	@staticmethod
	def make_sure_path_exists(path):
		""" Make sure a path exists.

		Source: http://stackoverflow.com/a/5032238
		Authors: StackOverflow users "Heikko Toivono" (http://stackoverflow.com/users/62596/heikki-toivonen) 
		 		and "Bengt" (http://stackoverflow.com/users/906658/bengt)
		"""
		try:
			os.makedirs(path)
		except OSError as exception:
			if exception.errno != errno.EEXIST:
				raise

	def get_config_from_cmdline(self):
		parser = self.get_argument_parser()
		args = parser.parse_args()

		run_dir = args.run_dir.rstrip(os.sep) + os.sep

		# checks?
		config = {}
		config['port'] = args.port
		config['run_dir'] = run_dir
		config['disk_quota'] = args.disk_quota
		config['max_file_size'] = args.max_file_size
		config['template_dir'] = args.template_dir.rstrip(os.sep)
		config['static_dir'] = args.static_dir.rstrip(os.sep)
		config['cookie_key'] = args.cookie_key
		return config

	def find_runs(self):
		base = os.path.basename(self.run_dir)
		runs = set()
		for w in os.walk(self.run_dir):
			b = os.path.basename(w[0])
			if b != base:
				runs.add(GSRun(b))
		return runs

	def run(self):
		self.app.listen(self.port)
		tornado.ioloop.IOLoop.current().start()

def main(config=None):
	server = GOPCAServer(config)
	server.run()
	return 0

if __name__ == "__main__":
	return_code = main()
	sys.exit(return_code)
