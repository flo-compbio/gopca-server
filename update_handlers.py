import sys
import os
import re
import subprocess as subproc
import ftplib
import urllib2
from contextlib import closing

import numpy as np
import tornado.web

import common

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
		self.data['gene_annotations'] = common.find_gene_annotations(self.data_dir)
		#print sp,data; sys.stdout.flush()

class GOAnnotationUpdateHandler(tornado.web.RequestHandler):
	def initialize(self,data):
		self.data = data

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

	def get_current_versions(self):
		versions = {}
		with closing(urllib2.urlopen('ftp://ftp.ebi.ac.uk/pub/databases/GO/goa/current_release_numbers.txt')) as uh:
			uh.readline()
			for l in uh:
				print l
				fields = l.rstrip('\n').split('\t')
				print fields
				versions[fields[0]] = [fields[1],fields[2]]
		return versions

	def post(self):
		server = 'ftp.ebi.ac.uk'
		user = 'anonymous'
		ftp = ftplib.FTP(server)
		ftp.login(user)

		#go_dir = 'pub'
		#ftp.cwd(go_dir)

		# get latest version
		versions = self.get_current_versions()

		# naming scheme: species_version_date.gaf.gz
		for sp in self.species:
			remote_dir = '/pub/databases/GO/goa/%s' %(sp.upper())
			remote_name = 'gene_association.goa_%s.gz' %(sp.lower())
			remote_path = '%s/%s' %(remote_dir,remote_name)
			url = 'ftp://%s%s' %(server,remote_path)
			name = '%s_%s_%s.gaf.gz' %(sp,versions[sp][0],versions[sp][1])
			output_file = self.data_dir + os.sep + name

			# get remote file size
			remote_size = ftp.size(remote_path)
			print name,'Remote file size:',remote_size

			# check if we need to download the file
			if os.path.isfile(output_file) and os.path.getsize(output_file) == remote_size:
				continue

			# download file
			print 'Downloading file "%s"...' %(url); sys.stdout.flush()
			with closing(urllib2.urlopen(url)) as uh, open(output_file,'wb') as ofh:
				ofh.write(uh.read())

			# make sure download was successful
			if (not os.path.isfile(output_file)) or (os.path.getsize(output_file) != remote_size):
				print 'Download unsuccessful! Deleting file...'
				if os.path.isfile(output_file): # race condition?
					os.remove(output_file)

			
			# read corresponding gene ontology version
		self.data['go_annotations'] = common.find_go_annotations(self.data_dir)
