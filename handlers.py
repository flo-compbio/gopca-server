# -*- coding: utf-8 -*-

import time
import hashlib

import tornado.web
import numpy as np

class TemplateHandler(tornado.web.RequestHandler):

	def initialize(self,data):
		self.data = data
		self.runs = data['runs']
		self.template_env = data['template_env']

	def get_template(self,fn):
		return self.template_env.get_template(fn)

class MainHandler(TemplateHandler):

	def initialize(self,data):
		super(MainHandler,self).initialize(data)
		#self.data = data

	def get_session_id(self):

		session_id = ''
		while not session_id:
			ts = str(time.time())
			ip = self.request.remote_ip
			rnd = str(np.random.random())[2:]
			h = hashlib.md5()
			h.update(ts)
			h.update(ip)
			h.update(rnd)
			session_id = h.hexdigest()

			# check if ID already exists (even though it's very unlikely)
			if session_id in self.runs:
				session_id = ''

		return session_id

	def get(self,path):
		template = self.get_template('index.html')
		new = self.get_query_argument('new',default='0')
		print "new:",new
		session_id = None
		if not (new == '1'): # we're not explicitly asked to start a new session
			session_id = self.get_secure_cookie('session_id') # look for session cookie
		if session_id is None: # new session (either asked explicitly, or no old session found)
			session_id = self.get_session_id() # generate a new session ID
		ts = str(time.time())
		html_output = template.render(timestamp=ts,title='Main Page',new=new,\
				runs=self.runs,session_id=session_id)
		self.write(html_output)

class SubmitHandler(TemplateHandler):

	def initialize(self,data):
		super(SubmitHandler,self).initialize(data)

	def post(self):
		session_id = self.get_body_argument('session_id')
		self.set_secure_cookie('session_id',session_id)
		self.write(session_id)

class RunHandler(TemplateHandler):

	def initialize(self,data):
		super(RunHandler,self).initialize(data)
		#self.data = data

	def get(self,path):
		self.write('Run!')


