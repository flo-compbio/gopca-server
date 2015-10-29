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
#   yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, tornado.ioloop.IOLoop.instance().time() + timeout)

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
        self.config = data['config']
        self.runs = data['runs']
        self.gene_annotations = data['gene_annotations']
        self.go_annotations = data['go_annotations']
        self.template_env = data['template_env']
        self.ts = str(time.time())

    @property
    def logger(self):
        return self.data['logger']

    @property
    def species(self):
        return self.data['species']

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

        session_id = None
        if not (new == '1'): # we're not explicitly asked to start a new session
            session_id = self.get_secure_cookie('session_id') # look for session cookie

        if session_id is not None:
            self.redirect('/run/%s' %(session_id))
            return

        # reload even when using back button on Firefox
        # (I tested it and it doesn't work without no-store)
        # see http://blog.55minutes.com/2011/10/how-to-defeat-the-browser-back-button-cache/
        self.add_header('Cache-Control','no-store, max-age=0, no-cache, must-revalidate')
        #self.add_header('Expires','0')
        #self.add_header('Pragma','no-cache')
        # new session (either asked explicitly, or no old session found)
        session_id = self.get_session_id() # generate a new session ID
        self.logger.debug('Species: %s', ', '.join(self.species))
        run_ids = sorted(self.runs.keys())
        html_output = template.render(timestamp=self.ts,title='Main Page',new=new,\
                runs=run_ids,species=self.species,gene_annotations=self.gene_annotations,go_annotations=self.go_annotations,\
                session_id=session_id)
        self.write(html_output)

class RunHandler(TemplateHandler):

    def initialize(self,data):
        super(RunHandler,self).initialize(data)

    def get(self,path):
        self.logger.debug('RunHandler path: %s',path)
        if path in self.runs: # and re.match(HASH_PATTERN) # to ensure that user cannot submit crap
            template = self.get_template('run.html')
            html_output = template.render(timestamp=self.ts,title='Run',run_id=path)
            self.write(html_output)
        else:

            session_id = self.get_secure_cookie('session_id')
            if session_id is not None and session_id == path:
                self.clear_cookie('session_id')

            template = self.get_template('404.html')
            html_output = template.render(timestamp=self.ts,title='Error 404 - page not found')
            self.write(html_output)
