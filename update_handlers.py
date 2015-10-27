import sys
import os
import csv
import re
import gzip
import subprocess as subproc
import ftplib
import urllib2
#import requests
from contextlib import closing

import numpy as np
import tornado.web

from items import GSGeneAnnotation,GSGoAnnotation

import common

class GeneAnnotationUpdateHandler(tornado.web.RequestHandler):
	def initialize(self,data):
		self.data = data

	@property
	def species_names(self):
		return self.data['species_names']

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
		for spec in self.species:

			spec_name = self.species_names[spec]

			# find the precise name of the GTF file that we're interested in
			spdir = 'pub/release-%d/gtf/%s' %(latest,spec.lower())
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
		self.data['gene_annotations'] = GSGeneAnnotation.find_gene_annotations(self.data_dir)

class GOAnnotationUpdateHandler(tornado.web.RequestHandler):
	def initialize(self,data):
		self.data = data

	@property
	def config(self):
		return self.data['config']

	@property
	def species_names(self):
		return self.data['species_names']

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

	def get_gaf_ontology_version(self,gaf_file):
		version_pat = re.compile(r'!GO-version: .*/(\d{4}-\d\d-\d\d)/go\.owl$')
		version = None
		with gzip.open(gaf_file) as fh:
		    reader = csv.reader(fh,dialect='excel-tab')
		    l = reader.next()
		    while l and l[0].startswith('!'):
		        m = version_pat.match(l[0])
		        if m is not None:
		            version = m.group(1)
		        l = reader.next()
		return version

	def get_obo_url(self,version):
		url = 'http://viewvc.geneontology.org/viewvc/GO-SVN/ontology-releases/%s/' %(version)
		body = common.read_url(url)
		revision_pat = re.compile(r'<a href="/viewvc/GO-SVN\?view=revision&amp;revision=(\d+)"')
		m = revision_pat.search(body)
		rev = m.group(1)
		obo_url = 'http://viewvc.geneontology.org/viewvc/GO-SVN/ontology-releases/%s/go-basic.obo?revision=%s' %(version,rev)
		return obo_url

	def post(self):
		server = 'ftp.ebi.ac.uk'
		user = 'anonymous'
		ftp = ftplib.FTP(server)
		ftp.login(user)

		#go_dir = 'pub'
		#ftp.cwd(go_dir)
		version_pat = re.compile(r'!GO-version: .*/(\d{4}-\d\d-\d\d)/go\.owl$')
		revision_pat = re.compile(r'<a href="/viewvc/GO-SVN\?view=revision&amp;revision=(\d+)"')

		# get latest version
		versions = self.get_current_versions()

		# naming scheme: species_version_date.gaf.gz
		for spec in self.species:

			name = self.species_names[spec]

			# locate the GAF file on the GOA server
			remote_dir = '/pub/databases/GO/goa/%s' %(name.upper())
			remote_file = 'gene_association.goa_%s.gz' %(name.lower())
			remote_path = '%s/%s' %(remote_dir,remote_file)
			url = 'ftp://%s%s' %(server,remote_path)
			file_name = '%s_%s_%s.gaf.gz' %(spec,versions[name][0],versions[name][1])

			# get file size
			remote_size = ftp.size(remote_path)
			print 'Remote file size:',remote_size

			# check if we need to download the file by comparing it to the local file (if it exists)
			gaf_file = self.data_dir + os.sep + file_name
			if os.path.isfile(gaf_file) and os.path.getsize(gaf_file) == remote_size:
				continue # also skip downloading OBO file

			# download file
			print 'Downloading file "%s"...' %(url); sys.stdout.flush()
			common.download_url(url,gaf_file)

			# make sure download was successful
			if (not os.path.isfile(gaf_file)) or (os.path.getsize(gaf_file) != remote_size):
				print 'Download unsuccessful! Deleting file...'
				if os.path.isfile(gaf_file): # race condition?
					os.remove(gaf_file)

			# get corresponding gene ontology version fromt the header of the GAF file
			version = self.get_gaf_ontology_version(gaf_file)
			# get the url of the corresponding "go-basic.obo" file on the GO SVN server
			url = self.get_obo_url(version)
			obo_file = self.data_dir + os.sep + '%s_%s_%s.obo' %(spec,versions[name][0],versions[name][1])
			# download the obo file
			common.download_url(url,obo_file)

		self.data['go_annotations'] = GSGoAnnotation.find_go_annotations(self.data_dir)
