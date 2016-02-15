import os
from collections import Counter
import json
import codecs

import datetime
import dateutil
import dateutil.parser

class JobData(object):
    pass

class GeneAnnotationData(object):

    def __init__(self,name):
        self.name = name

    @property
    def file_name(self):
        return self.name + '.gtf.gz'

    @classmethod
    def find_gene_annotations(cls, data_dir):
        annotations = set()
        for f in os.listdir(data_dir):
            #print f
            if os.path.isfile(data_dir + os.sep + f) and f.endswith('.gtf.gz'):
                annotations.add(cls(f[:-7]))

        annotations = sorted(annotations, key=lambda a:a.name)
        return annotations

class GOAnnotationData(object):

    def __init__(self, name):
        self.name = name

    @classmethod
    def find_go_annotations(cls, data_dir):
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

        annotations = sorted(annotations, key = lambda a:a.name)
        return annotations

    @property
    def ontology_file_name(self):
        return self.name + 'obo'

    @property
    def association_file_name(self):
        return self.name + '.gaf.gz'
