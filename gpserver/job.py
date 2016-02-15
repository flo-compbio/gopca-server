import os
import codecs
import json
import datetime
import logging

logger = logging.getLogger(__name__)

class GSJob(object):

    RUNNING = 0
    FINISHED = 1
    FAILED = 2

    UTF8Writer = codecs.getwriter('utf8')

    data_file_name = 'job_data.json'

    def __init__(self, id_, dir_, desc, submit_time, species, status = None):

        assert isinstance(submit_time, datetime.datetime)
        # we only support UTC time
        assert (submit_time.tzinfo is None) or \
                isinstance(submit_time.tzinfo, dateutil.tz.tzutc)

        self.id = id_
        self.dir_ = run_dir_
        self.submit_time = submit_time
        self.desc = desc
        self.species = species
        self.status = status

    def __repr__(self):
        return '<GSJob - ID "%s">' %(self.id)

    def __str__(self):
        status = str(self.status)
        submit_time = self.get_json_datetime(self.submit_time)
        return '<GSJob: ID=%s, submit time=%s, description=%s, species=%s, run_dir=%s, status=%s>' \
                %(self.id,self.submit_time,self.description,self.species,self.run_dir,self.status)

    @classmethod
    def find_jobs(cls, job_dir):
        base = os.path.basename(job_dir)
        jobs = {}
        for w in os.walk(job_dir):
            b = os.path.basename(w[0])
            if b != base:
                data_file = job_dir + os.sep + b + os.sep + GSJob.data_file_name
                jobs[b] = cls.load_json(data_file)
                jobs[b].update_status()
        logger.debug('Found %d jobs.', len(jobs))
        return jobs

    #def __repr__(self):

    @property
    def is_running(self):
        if self.status == self.RUNNING:
            return True
        else:
            return False

    @property
    def has_failed(self):
        if self.status == self.FAILED:
            return True
        else:
            return False

    @property
    def has_finished(self):
        if self.status == self.FINISHED:
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
        return dateutil.parser.parse(dt).replace(tzinfo = None)

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
        elif self.status == self.FINISHED:
            return '<span style="color: #007F00; font-weight: bold">Finished</span>'
        elif self.status == self.FAILED:
            return '<span style="color: #7F0000; font-weight: bold">Failed</span>'
        elif self.status is None:
            return 'Internal Server Error'

    def write_json(self, output_file):
        json_submit_time = self.get_json_datetime(self.submit_time)
        data = {'id': self.id, 'submit_time': json_submit_time, 'run_dir': self.run_dir, 'species': self.species, 'description': self.description}
        with codecs.open(output_file, 'wb', encoding = 'utf-8') as ofh:
            #writer = self.UTF8Writer(ofh)
            json.dump(data, ofh, ensure_ascii=False, encoding = 'utf8')

    #def store_data(self):
    #    output_file = self.run_dir + os.sep + self.id + os.sep + self.data_file_name
    #    self.save_json(output_file)

    @classmethod
    def read_json(cls,data_file):
        data = None
        with open(data_file, 'rb') as fh:
            data = json.load(fh) # utf-8 by default
        submit_time = cls.parse_json_datetime(data['submit_time'])
        return cls(data['id'],submit_time,data['run_dir'],data['species'],data['description'])

    def update_status(self):
        """ returns True if status has changed """
        # this function should be part of the server

        if (self.status is not None) and self.status > 0:
            # status is already final
            return False

        old_status = self.status
       
        job_dir = self.run_dir + os.sep + self.id

        if os.path.isfile(run_dir + os.sep + 'FAILURE'):
            self.status = self.FAILED
        elif os.path.isfile(run_dir + os.sep + 'FINISHED'):
            self.status = self.FINISHED
        else:
            self.status = self.RUNNING

        if self.status != old_status:
            return True
        else:
            return False
 
