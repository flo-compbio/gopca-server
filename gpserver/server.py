# Copyright (c) 2015 Florian Wagner, Razvan Panea
#
# This file is part of GO-PCA Server.
#
# GO-PCA Server is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, Version 3,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import argparse
import errno
import time
import shutil
import logging
import ssl
from copy import deepcopy

from jinja2 import Environment, FileSystemLoader

import tornado.ioloop
import tornado.web
import tornado.httpserver

from tornado.concurrent import return_future
from tornado import gen

from tornado.httpclient import AsyncHTTPClient

import numpy as np

from genometools import misc

from gpserver.data import GeneAnnotationData, GOAnnotationData
from gpserver.handlers import *
from gpserver.update_handlers import *
from gpserver.gopca_handlers import *
from gpserver.signature_handler import *
from gpserver import util
from gpserver import GSJob

@tornado.web.asynchronous
def future_func(callback):
    print 'Sleeping...'; sys.stdout.flush()
    time.sleep(5)
    print 'done!'; sys.stdout.flush()

#@gen.engine
#def caller():
#   yield future_func()

logger = logging.getLogger(__name__)

class GOPCAServer(object):

    species_names = {
        'Homo_sapiens': 'human',
        'Mus_musculus': 'mouse'
    }

    def __init__(self, config):

        config = deepcopy(config)

        # modify config values here if necessary
        if config.seed is None:
            config.seed = np.random.randint(int(1e9))

        if config.port is None:
            if config.ssl_dir is not None:
                config.port = 443
            else:
                config.port = 80

        self.config = config
        self.counter = 0

        # seed the random number generator
        np.random.seed(config.seed)

        # define root, template and static directories
        self.root_dir = os.path.dirname(os.path.abspath(__file__))\
                .rstrip(os.sep)
        self.template_dir = self.root_dir + os.sep + 'templates'
        self.static_dir = self.root_dir + os.sep + 'static'

        logger.debug('Root directory: %s', self.root_dir)

        # make sure run and data directories exist
        misc.make_sure_dir_exists(self.job_dir, create_subfolders = False)
        misc.make_sure_dir_exists(self.data_dir, create_subfolders = False)

        self.template_loader = FileSystemLoader(searchpath = self.template_dir)
        self.template_env = Environment(loader = self.template_loader)

        self.jobs = GSJob.find_jobs(self.job_dir)
        self.gene_annotations = GeneAnnotationData.find_gene_annotations(self.data_dir)
        self.go_annotations = GOAnnotationData.find_go_annotations(self.data_dir)

        logger.debug('Gene annotations: %s',
                ', '.join(str(ann) for ann in self.gene_annotations))
        logger.debug('GO annotations: %s',
                ', '.join(str(ann) for ann in self.go_annotations))
        logger.debug('Jobs: %s',
                ', '.join(str(j) for j in self.jobs))

        # data is a dictionary holding all the server data (while it's running)
        data = {'config': self.config,
                'gene_annotations': self.gene_annotations,
                'go_annotations': self.go_annotations,
                'jobs': self.jobs,
                'template_loader': self.template_loader,
                'template_env': self.template_env,
                'species_names': self.species_names,
        }

        self.app = tornado.web.Application([
                (r'/static/(.*)$', tornado.web.StaticFileHandler,
                    {'path': self.static_dir}),
                (r'/gopca$', GOPCAHandler, dict(data = data), 'submit'),
                (r'/delete-job$', DeleteJobHandler, dict(data = data),
                    'delete-job'),
                (r'/update-gene-annotations$', GeneAnnotationUpdateHandler,
                    dict(data = data), 'update-gene-annotations'),
                (r'/update-go-annotations$', GOAnnotationUpdateHandler,
                    dict(data = data), 'update-go-annotations'),
                (r'/job/([0-9a-f]{32}/(?:gopca_pipeline_log\.txt|gopca_signature_matrix\.png|gopca_signatures\.tsv|gopca_signatures\.xlsx))$',
                    tornado.web.StaticFileHandler, {'path': self.job_dir}),
                (r'/job/([0-9a-f]{32})$', JobHandler,
                    dict(data = data), 'job'),
                (r'/job/([0-9a-f]{32})/signature/(-?[0-9]+)$',
                    SignatureHandler, dict(data = data), 'signature'),
                (r'/sleep/(\d+)$', SleepHandler,{},'sleep'),
                (r'/(.*)$', MainHandler, dict(data = data), 'main'),
        ])
        #], cookie_secret=self.cookie_key)
        
        self.ssl_ctx = None
        if self.ssl_dir is not None:
            #util.make_sure_path_exists(self.ssl_dir)
            self.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_ctx.load_cert_chain(os.path.join(self.ssl_dir, "server.crt"), os.path.join(self.ssl_dir, "server.key"))
    
        self.server = tornado.httpserver.HTTPServer(self.app, ssl_options = self.ssl_ctx)

    @property
    def port(self):
        return self.config.port

    @property
    def job_dir(self):
        return self.config.job_dir

    @property
    def data_dir(self):
        return self.config.data_dir

    @property
    def ssl_dir(self):
        return self.config.ssl_dir

    #@property
    #def cookie_key(self):
    #    return self.config['cookie_key']

    """
    @gen.coroutine
    def update(self):
        print 'Update:',self.counter
        respone = yield time.sleep(10)
        self.counter += 1
    """

    def run(self):
        self.server.listen(self.config.port)
        #ioloop = tornado.ioloop.IOLoop.instance()

        #self.update_task = tornado.ioloop.PeriodicCallback(future_func,2*1000)
        #self.update_task.start()
        #tornado.ioloop.IOLoop.current().add_callback(self.update)

        tornado.ioloop.IOLoop.current().start()
