# -*- coding: utf-8 -*-

import sys
import os
import time
import hashlib
import ftplib
import logging
import re
import urllib2
import math
from contextlib import closing
import subprocess as subproc

import tornado.web
import numpy as np

import tornado

#from gopca import common
from gopca import util

logger = logging.getLogger(__name__)

#from tornado import gen
#@tornado.gen.coroutine
#def async_sleep(timeout):
#   yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, tornado.ioloop.IOLoop.instance().time() + timeout)
sign = lambda x:int(math.copysign(1.0,x))

class SleepHandler(tornado.web.RequestHandler):

    @tornado.gen.coroutine
    def get(self, n):
        #async_sleep(float(n))
        yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, tornado.ioloop.IOLoop.instance().time() + float(n))
        self.write("Awake! %s" % time.time())
        self.finish()

class GSHandler(tornado.web.RequestHandler):

    def initialize(self, data):
        self.data = data
        #self.timestamp = 
        self.ts = str(time.time())

    @property
    def species(self):
        return self.config.species

    @property
    def species_names(self):
        return self.data['species_names']

    @property
    def config(self):
        return self.data['config']

    @property
    def jobs(self):
        return self.data['jobs']

    @property
    def gene_annotations(self):
        return self.data['gene_annotations']

    @property
    def go_annotations(self):
        return self.data['go_annotations']

    @property
    def template_env(self):
        return self.data['template_env']

    def get_template(self, name):
        return self.template_env.get_template(name)

    def generate_session_id(self):
        data = []
        data.append(str(time.time()))
        data.append(self.request.remote_ip)
        data.append(str(np.random.random())[2:])
        hash_str = ','.join(data)
        session_id = hashlib.md5(hash_str).hexdigest()
        return session_id

class MainHandler(GSHandler):

    def initialize(self,data):
        super(MainHandler, self).initialize(data)
        #self.data = data

    def update_job_status(self, job):
        if (job.status is not None) and (job.status > 0):
            # status is already final
            return False

        dir_ = self.job_dir + os.sep + job.id
        old_status = job.status
       
        if os.path.isfile(job_dir + os.sep + 'FAILED'):
            job.status = self.FAILED
        elif os.path.isfile(job_dir + os.sep + 'FINISHED'):
            job.status = self.FINISHED
        else:
            job.status = self.RUNNING

        if job_status != old_status:
            job.store_data()
        return job.status != old_status

    def update_all_job_statuses(self):
        for id_,job in self.jobs:
            self.update_job_status(job)

    """
    # should be job id
    def get_session_id(self):

        session_id = ''
        while not session_id:
            ts = str(time.time())
            ip = self.request.remote_ip
            rnd = str(np.random.random())[2:]
            session_id = self.generate_session_id()

            # check if ID already exists (even though it's very unlikely)
            if session_id in self.job:
                session_id = ''

        return session_id
    """

    def update_job_status(self):
        # needs to do the whole job
        for id_,r in self.runs.iteritems():
            if r.update_status():
                r.store_data()

    def get(self,path):
        template = self.get_template('index.html')
        #new = self.get_query_argument('new',default='0')

        logger.debug('Jobs: %s',
                ','.join([str(id_) for id_ in self.jobs.values()]))

        #session_id = None
        #if not (new == '1'): # we're not explicitly asked to start a new session
        #    session_id = self.get_secure_cookie('session_id') # look for session cookie

        #if session_id is not None:
        #    self.redirect('/run/%s' %(session_id))
        #    return

        self.update_all_job_statuses()

        # reload even when using back button on Firefox
        # (I tested it and it doesn't work without no-store)
        # see http://blog.55minutes.com/2011/10/how-to-defeat-the-browser-back-button-cache/
        self.add_header('Cache-Control','no-store, max-age=0, no-cache, ' +
                'must-revalidate')
        #self.add_header('Expires','0')
        #self.add_header('Pragma','no-cache')

        # new session (either asked explicitly, or no old session found)
        #session_id = self.get_session_id() # generate a new session ID
        #logger.debug('Species: %s', ', '.join(self.species))

        job_ids = sorted(self.jobs.keys())
        jobs = sorted(self.jobs.values(), key=lambda r: r.submit_time)
        html_output = template.render(timestamp = self.ts, title = 'Main Page',
                jobs = jobs, species = self.species,
                gene_annotations = self.gene_annotations,
                go_annotations = self.go_annotations)
        self.write(html_output)

class JobHandler(GSHandler):

    def initialize(self,data):
        super(JobHandler,self).initialize(data)
        self.run_dir = self.config['run_dir']

    def get(self,run_id):
        self.logger.debug('RunHandler ID: %s', run_id)
        if run_id in self.runs: # and re.match(HASH_PATTERN) # to ensure that user cannot submit crap

            run = self.runs[run_id]

            # check status
            if run.update_status():
                run.store_data()

            if run.is_running: # status: running
                template = self.get_template('run_running.html')
                html_output = template.render(timestamp=self.ts,title='Run',run_id=run_id,update_seconds=3)

            elif run.has_failed:
                html_output = 'This run has failed'

            elif run.has_succeeded:
                template = self.get_template('run.html')
                gopca_file = self.run_dir + os.sep + run_id + os.sep + 'gopca_result.pickle'
                self.logger.debug('GO-PCA file: %s', gopca_file)
                result = util.read_gopca_result(gopca_file)
                signatures = result.signatures
                signatures = sorted(signatures, key = lambda sig:
                        [abs(sig.pc), -sign(sig.pc), -sig.escore])
                html_output = template.render(timestamp = self.ts,
                        title = 'Job', run_id = run_id, signatures=signatures)
            self.write(html_output)
        else:

            session_id = self.get_secure_cookie('session_id')
            if session_id is not None and session_id == path:
                self.clear_cookie('session_id')

            template = self.get_template('404.html')
            html_output = template.render(timestamp=self.ts,title='Error 404 - page not found')
            self.write(html_output)
