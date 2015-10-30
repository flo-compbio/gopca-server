import os
from collections import Counter
import json
import codecs

import datetime
import dateutil
import dateutil.parser

class GSRun(object):

    RUNNING = 0
    SUCCESSFUL = 1
    FAILED = 2

    UTF8Writer = codecs.getwriter('utf8')

    data_file_name = 'run_data.json'

    def __init__(self,id_,submit_time,run_dir,species,description,status=None):

        assert (submit_time.tzinfo is None) or isinstance(submit_time.tzinfo,dateutil.tz.tzutc) # we only support UTC time

        self.id = id_
        self.submit_time = submit_time
        self.run_dir = run_dir
        self.description = description
        self.species = species
        self.status = status

    def __repr__(self):
        return '<GSRun - ID "%s">' %(self.id)

    def __str__(self):
        status = str(self.status)
        submit_time = self.get_json_datetime(self.submit_time)
        return '<GSRun: ID=%s, submit time=%s, description=%s, species=%s, run_dir=%s, status=%s>' \
                %(self.id,self.submit_time,self.description,self.species,self.run_dir,self.status)

    @classmethod
    def find_runs(cls,run_dir):
        base = os.path.basename(run_dir)
        runs = {}
        for w in os.walk(run_dir):
            b = os.path.basename(w[0])
            if b != base:
                data_file = run_dir + os.sep + b + os.sep + GSRun.data_file_name
                runs[b] = cls.load_json(data_file)
                runs[b].update_status()
        return runs

    #def __repr__(self):

    @property
    def is_running(self):
        if self.status == self.RUNNING:
            return True
        else:
            return False

    def __eq__(self,other):
        if type(other) != type(self):
            return False
        elif hash(self) == hash(other):
            return True
        else:
            return False

    def __hash__(self):
        return hash((self.id,self.run_dir))

    @staticmethod
    def get_current_time():
        # returns current UTC time as datetime object
        # truncate microseconds
        return datetime.datetime.utcnow().replace(microsecond=0)

    @staticmethod
    def get_json_datetime(dt):
        # conforms to RFC 3339
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def parse_json_datetime(dt):
        # use parser from dateutil package to parse RFC 3339-compliant date
        return dateutil.parser.parse(dt).replace(tzinfo=None)

    @property
    def submit_time_json(self):
        return self.get_json_datetime(self.submit_time)

    @property
    def submit_time_html(self):
        return self.submit_time.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def status_html(self):
        if self.status is None:
            return 'Internal Server Error'
        elif self.status == self.RUNNING:
            return '<span style="color: orange; font-weight: bold">Running</span>'
        elif self.status == self.SUCCESSFUL:
            return '<span style="color: #007F00; font-weight: bold">Complete</span>'
        elif self.status == self.FAILED:
            return '<span style="color: #7F0000; font-weight: bold">Failed</span>'
        elif self.status is None:
            return 'Internal Server Error'

    def save_json(self,output_file):
        json_submit_time = self.get_json_datetime(self.submit_time)
        data = {'id': self.id, 'submit_time': json_submit_time, 'run_dir': self.run_dir, 'species': self.species, 'description': self.description}
        with open(output_file,'wb') as ofh:
            writer = self.UTF8Writer(ofh)
            json.dump(data,writer,ensure_ascii=False,encoding='utf8')

    def store_data(self):
        output_file = self.run_dir + os.sep + self.id + os.sep + self.data_file_name
        self.save_json(output_file)

    @classmethod
    def load_json(cls,data_file):
        data = None
        with open(data_file,'rb') as fh:
            data = json.load(fh,encoding='utf8')
        submit_time = cls.parse_json_datetime(data['submit_time'])
        return cls(data['id'],submit_time,data['run_dir'],data['species'],data['description'])

    def update_status(self):
        """ returns True if status has changed """

        old_status = self.status

        if (self.status is not None) and self.status > 0:
            # status is already final
            return False
        
        run_dir = self.run_dir + os.sep + self.id

        if os.path.isfile(run_dir + os.sep + 'FAILURE'):
            self.status = self.FAILED
        elif os.path.isfile(run_dir + os.sep + 'SUCCESS'):
            self.status = self.SUCCESSFUL
        else:
            self.status = self.RUNNING

        if self.status != old_status:
            return True
        else:
            return False
        
class GSGeneAnnotation(object):

    def __init__(self,name):
        self.name = name

    @property
    def file_name(self):
        return self.name + '.gtf.gz'

    @classmethod
    def find_gene_annotations(cls,data_dir):
        annotations = set()
        for f in os.listdir(data_dir):
            #print f
            if os.path.isfile(data_dir + os.sep + f) and f.endswith('.gtf.gz'):
                annotations.add(cls(f[:-7]))

        annotations = sorted(annotations, key=lambda a:a.name)
        return annotations

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

        annotations = sorted(annotations,key=lambda a:a.name)
        return annotations

    @property
    def ontology_file_name(self):
        return self.name + 'obo'

    @property
    def association_file_name(self):
        return self.name + '.gaf.gz'
