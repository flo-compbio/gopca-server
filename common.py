# -*- coding: utf-8 -*-

import os
import urllib2
from contextlib import closing
from collections import Counter

from items import *

def find_runs(run_dir):
	base = os.path.basename(run_dir)
	runs = set()
	for w in os.walk(run_dir):
		b = os.path.basename(w[0])
		if b != base:
			runs.add(GSRun(b))
	return runs

def find_gene_annotations(data_dir):
	annotations = set()
	for f in os.listdir(data_dir):
		#print f
		if os.path.isfile(data_dir + os.sep + f) and f.endswith('.gtf.gz'):
			annotations.add(GSGeneAnnotation(f))
	return annotations

def find_go_annotations(data_dir):
	annotations = set()
	
	C = Counter()
	for f in os.listdir(data_dir):
		if os.path.isfile(data_dir + os.sep + f):
			if f.endswith('.gaf.gz'):
				C[f[:-7]] += 1
			elif f.endswith('.obo'):
				C[f[:-4]] += 1

	for f in C:
		if C[f] == 2:
			annotations.add(GSGOAnnotation(f))
	return annotations

def download_url(url,output_file):
	with closing(urllib2.urlopen(url)) as uh, open(output_file,'wb') as ofh:
		ofh.write(uh.read())

def read_url(url):
	body = None
	with closing(urllib2.urlopen(url)) as uh:
		body = uh.read()
	return body
