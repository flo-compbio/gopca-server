#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import errno
import time
import shutil
import logging
import ssl

from jinja2 import Environment, FileSystemLoader

import tornado.ioloop
import tornado.web
import tornado.httpserver

from tornado.concurrent import return_future
from tornado import gen

from tornado.httpclient import AsyncHTTPClient

from items import GSRun,GSGeneAnnotation,GSGoAnnotation
from handlers import *
from update_handlers import *
from gopca_handlers import *
import util

@tornado.web.asynchronous
def future_func(callback):
    print 'Sleeping...'; sys.stdout.flush()
    time.sleep(5)
    print 'done!'; sys.stdout.flush()

#@gen.engine
#def caller():
#   yield future_func()

class GOPCAServer(object):

    species_names = {
        'Homo_sapiens': 'human',
        'Mus_musculus': 'mouse'
    }

    def __init__(self,config=None):

        self.counter = 0

        if config is None:
            config = self.get_config_from_cmdline()

        self.config = config

        # make sure run directory exists
        util.make_sure_path_exists(self.run_dir)
        util.make_sure_path_exists(self.data_dir)

        self.template_loader = FileSystemLoader(searchpath = self.template_dir)
        self.template_env = Environment(loader = self.template_loader )

        self.runs = GSRun.find_runs(self.run_dir)
        self.gene_annotations = GSGeneAnnotation.find_gene_annotations(self.data_dir)
        self.go_annotations = GSGoAnnotation.find_go_annotations(self.data_dir)

        # configure logger
        log_level = logging.INFO
        if config['verbose']:
            log_level = logging.DEBUG

        log_format = '[%(asctime)s] %(levelname)s: %(message)s'
        log_datefmt = '%Y-%m-%d %H:%M:%S'
        # when filename is not None, "stream" parameter is ignored (see https://docs.python.org/2/library/logging.html#logging.basicConfig)
        logging.basicConfig(filename=config['log_file'],stream=sys.stdout,level=log_level,format=log_format,datefmt=log_datefmt)
        self.logger = logging.getLogger()
        logger = self.logger

        logger.info('Gene annotations: %s', ', '.join(str(ann) for ann in self.gene_annotations))
        logger.info('GO annotations: %s', ', '.join(str(ann) for ann in self.go_annotations))
        logger.info('Runs: %s', ', '.join(str(r) for r in self.runs))
        data = {'runs': self.runs,\
                'gene_annotations': self.gene_annotations,\
                'go_annotations': self.go_annotations,\
                'config': self.config, \
                'template_loader': self.template_loader, \
                'template_env': self.template_env,\
                'species': self.species,\
                'species_names': self.species_names,\
                'logger': self.logger}

        self.app = tornado.web.Application([
            (r'/static/(.*)$', tornado.web.StaticFileHandler, {'path': self.static_dir}),
            (r'/gopca$', GOPCAHandler,dict(data=data),'submit'),
            (r'/delete-run$', DeleteRunHandler,dict(data=data),'delete-run'),
            (r'/update-gene-annotations$', GeneAnnotationUpdateHandler,dict(data=data),'update-gene-annotations'),
            (r'/update-go-annotations$', GOAnnotationUpdateHandler,dict(data=data),'update-go-annotations'),
            (r'/run/(.*)$', RunHandler,dict(data=data),'run'),
            #(r'/sleep/(\d+)$', SleepHandler,{},'sleep'),
            (r'/(.*)$', MainHandler,dict(data=data),'main'),
        ], cookie_secret=self.cookie_key)
        
        self.ssl_ctx = None
        if self.ssl_dir is not None:
            util.make_sure_path_exists(self.ssl_dir)

            self.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_ctx.load_cert_chain(os.path.join(self.ssl_dir, "server.crt"), os.path.join(self.ssl_dir, "server.key"))
    
        self.server = tornado.httpserver.HTTPServer(self.app, ssl_options=self.ssl_ctx)

    @property
    def port(self):
        return self.config['port']

    @property
    def species(self):
        return self.config['species']

    @property
    def run_dir(self):
        return self.config['run_dir']

    @property
    def data_dir(self):
        return self.config['data_dir']

    @property
    def ssl_dir(self):
        return self.config['ssl_dir']

    @property
    def static_dir(self):
        return self.config['static_dir']

    @property
    def template_dir(self):
        return self.config['template_dir']

    @property
    def disk_quota(self):
        return self.config['disk_quota']

    @property
    def max_file_size(self):
        return sef.config['max_file_size']

    @property
    def cookie_key(self):
        return self.config['cookie_key']

    @staticmethod
    def get_argument_parser():
        parser = argparse.ArgumentParser(description='GO-PCA web server')
        parser.add_argument('-k','--cookie-key',required=True,help='Secret cookie key')
        parser.add_argument('-p','--port',type=int,default=8080,help='Port that the server listens on')
        parser.add_argument('-r','--run-dir',default='runs',help='Directory for storing runs')
        parser.add_argument('-d','--data-dir',default='data',help='Directory for storing annotation data')
        parser.add_argument('-q','--disk-quota',type=float,default=5000.0,help='Maximal disk space to use, in MB')
        parser.add_argument('-f','--max-file-size',type=float,default=500.0,help='Maximal GO-PCA input size, in MB')
        parser.add_argument('-s','--species',nargs='+',default=['Homo_sapiens','Mus_musculus'])
        parser.add_argument('--ssl-dir',default=None,help='SSL certificate and private key directory')
        parser.add_argument('--template-dir',default='templates',help='Jinja2 template directory')
        parser.add_argument('--static-dir',default='static',help='Directory for static content')
        parser.add_argument('-l','--log-file',default=None,help='Log file - if not specified, print to stdout')
        parser.add_argument('-v','--verbose',action='store_true',help='Verbose output')

        return parser

    def get_config_from_cmdline(self):
        parser = self.get_argument_parser()
        args = parser.parse_args()

        # checks?
        config = {}
        config['port'] = args.port
        config['run_dir'] = args.run_dir.rstrip(os.sep)
        config['data_dir'] = args.data_dir.rstrip(os.sep)
        config['disk_quota'] = args.disk_quota
        config['max_file_size'] = args.max_file_size
        config['ssl_dir'] = args.ssl_dir
        config['template_dir'] = args.template_dir.rstrip(os.sep)
        config['static_dir'] = args.static_dir.rstrip(os.sep)
        config['cookie_key'] = args.cookie_key
        config['species'] = args.species
        config['log_file'] = args.log_file
        config['verbose'] = args.verbose
        return config

    """
    @gen.coroutine
    def update(self):
        print 'Update:',self.counter
        respone = yield time.sleep(10)
        self.counter += 1
    """

    def run(self):
        self.server.listen(self.port)
        #ioloop = tornado.ioloop.IOLoop.instance()

        #self.update_task = tornado.ioloop.PeriodicCallback(future_func,2*1000)
        #self.update_task.start()
        #tornado.ioloop.IOLoop.current().add_callback(self.update)

        tornado.ioloop.IOLoop.current().start()

def main(config=None):
    server = GOPCAServer(config)
    server.run()
    return 0

if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)
