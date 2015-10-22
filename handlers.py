# -*- coding: utf-8 -*-

import sys
import os
import time
import hashlib
import ftplib
import re
import urllib2
from contextlib import closing
import subprocess as subproc

import tornado.web
import numpy as np

import tornado

#from tornado import gen
#@tornado.gen.coroutine
#def async_sleep(timeout):
#	yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, tornado.ioloop.IOLoop.instance().time() + timeout)

class SleepHandler(tornado.web.RequestHandler):

	@tornado.gen.coroutine
	def get(self, n):
		#async_sleep(float(n))
		yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, tornado.ioloop.IOLoop.instance().time() + float(n))
		self.write("Awake! %s" % time.time())
		self.finish()

class TemplateHandler(tornado.web.RequestHandler):

	def initialize(self,data):
		self.data = data
		self.runs = data['runs']
		self.gene_annotations = data['gene_annotations']
		self.go_annotations = data['go_annotations']
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
				runs=self.runs,gene_annotations=self.gene_annotations,go_annotations=self.go_annotations,\
				session_id=session_id)
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

class GeneAnnotationUpdateHandler(tornado.web.RequestHandler):
	def initialize(self,data):
		self.data = data

	@property
	def scientific_names(self):
		return self.data['scientific_names']

	@property
	def config(self):
		return self.data['config']

	@property
	def species(self):
		return self.config['species']

	@property
	def data_dir(self):
		return self.config['data_dir']

	def test_checksums(self,path,checksum):
		if not os.path.isfile(path): # not a file
			return False

		# calculate checksum
		sub = subproc.Popen('sum %s' %(path),bufsize=-1,shell=True,stdout=subproc.PIPE)
		file_checksum = sub.communicate()[0].rstrip('\n')
		print "TEST:",file_checksum,checksum
		return file_checksum == checksum

	def post(self):
		server = 'ftp.ensembl.org'
		#go_dir = 'pub/current_gtf'
		go_dir = 'pub'
		user = 'anonymous'

		# get directory listnig
		ftp = ftplib.FTP(server)
		ftp.login(user)

		data = []
		#ftp.cwd(go_dir)
		ftp.dir(go_dir,data.append)
		#ftp.quit()

		# find everything that ends in release-xx
		pat = re.compile(r'.* release-(\d+)$')
		release_numbers = []
		for d in data:
			m = pat.match(d)
			if m is not None:
				release_numbers.append(m.group(1))

		release_numbers = np.int64(release_numbers)
		latest = np.amax(release_numbers)

		"""
		for sp in self.species:
			sc = self.scientific_names[sp].lower()
			spdir = 'pub/release-%d/gtf/%s' %(latest,sc)
			data = []
			#ftp.dir(spdir,data.append)
			cs_url = 'ftp://' + '/'.join([server,spdir,'CHECKSUMS'])
			print cs_url
			checksum = None
			with closing(urllib2.urlopen(cs_url)) as uh:
				checksum = uh.read()
			print sp,checksum; sys.stdout.flush()
		"""
		for sp in self.species:

			# find the precise name of the GTF file that we're interested in
			sc = self.scientific_names[sp].lower()
			spdir = 'pub/release-%d/gtf/%s' %(latest,sc)
			data = []
			ftp.dir(spdir,data.append)
			gtf_file = []
			for d in data:
				i = d.rindex(' ')
				fn = d[(i+1):]
				if fn.endswith('.%d.gtf.gz' %(latest)):
					gtf_file.append(fn)
			assert len(gtf_file) == 1
			gtf_file = gtf_file[0]
			#print gtf_file

			# download the CHECKSUMS file and create a mapping of file names to checksums
			data = []
			cs_path = '/'.join([spdir,'CHECKSUMS'])
			#print cs_path
			data = []
			ftp.retrbinary('RETR %s' %(cs_path),data.append)
			data = ''.join(data).split('\n')[:-1]
			checksums = {}
			for d in data:
				s,fn = d.split('\t')
				checksums[fn] = s

			# compare checksums to see if we need to download the file
			output_file = self.data_dir + os.sep + gtf_file
			if self.test_checksums(output_file,checksums[gtf_file]):
				print 'Checksums agree!'; sys.stdout.flush()
			else:
				print 'Downloading %s...' %(output_file); sys.stdout.flush()
				gtf_path = '/'.join([spdir,gtf_file])
				with open(output_file,'w') as ofh:
					ftp.retrbinary('RETR %s' %(gtf_path),ofh.write)

				print 'done!'; sys.stdout.flush()
				if not self.test_checksums(output_file,checksums[gtf_file]):
					print "ERROR: Checksums don't agree! Deleting downloaded file..."
					if os.path.isfile(output_file): # race condition?
						os.remove(output_file)
			
		# update gene annotations
		self.data['gene_annotations'] = find_gene_annotations(self.data_dir)
		#print sp,data; sys.stdout.flush()
