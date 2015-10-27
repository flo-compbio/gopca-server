import os
from collections import Counter

class GSRun(object):

	def __init__(self,id_):
		self.id = id_

	@classmethod
	def find_runs(cls,run_dir):
		base = os.path.basename(run_dir)
		runs = {}
		for w in os.walk(run_dir):
			b = os.path.basename(w[0])
			if b != base:
				runs[b] = cls(b)
		return runs

	def __eq__(self,other):
		if type(other) != type(self):
			return False
		elif other.id == self.id:
			return True
		else:
			return False

	def __hash__(self):
		return hash(self.id)

class GSGeneAnnotation(object):

	def __init__(self,name):
		self.name = name

	@classmethod
	def find_gene_annotations(cls,data_dir):
		annotations = set()
		for f in os.listdir(data_dir):
			#print f
			if os.path.isfile(data_dir + os.sep + f) and f.endswith('.gtf.gz'):
				annotations.add(cls(f[:-7]))
		return sorted(annotations)

	@property
	def file_name(self):
		return self.name + '.gtf.gz'

class GSGoAnnotation(object):

	def __init__(self,name):
		self.name = name

	@classmethod
	def find_go_annotations(cls,data_dir):
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
				annotations.add(cls(f))
		return sorted(annotations)

	@property
	def ontology_file_name(self):
		return self.name + 'obo'

	@property
	def association_file_name(self):
		return self.name + '.gaf.gz'
