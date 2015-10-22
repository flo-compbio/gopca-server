# -*- coding: utf-8 -*-

import os

from items import *

def find_runs(run_dir):
	base = os.path.basename(self.run_dir)
	runs = set()
	for w in os.walk(self.run_dir):
		b = os.path.basename(w[0])
		if b != base:
			runs.add(GSRun(b))
	return runs

def find_gene_annotations(data_dir):
	annotations = set()
	for f in os.listdir(self.data_dir):
		#print f
		if os.path.isfile(self.data_dir + os.sep + f) and f.endswith('.gtf.gz'):
			annotations.add(GSGeneAnnotation(f))
	return annotations

def find_go_annotations(data_dir):
	annotations = set()
	for f in os.listdir(self.data_dir):
		#print f
		if os.path.isfile(self.data_dir + os.sep + f) and f.endswith('.gaf.gz'):
			annotations.add(GSGOAnnotation(f))
