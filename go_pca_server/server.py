#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Florian Wagner, Razvan Panea

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

from go_pca_server.items import GSRun,GSGeneAnnotation,GSGoAnnotation
from go_pca_server.handlers import *
from go_pca_server.update_handlers import *
from go_pca_server.gopca_handlers import *
from go_pca_server.signature_handler import *
from go_pca_server import util

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

        # configure logger
        log_level = logging.INFO
        if config['quiet']:
            log_level = logging.WARNING
        elif config['verbose']:
            log_level = logging.DEBUG

        log_format = '[%(asctime)s] %(levelname)s: %(message)s'
        log_datefmt = '%Y-%m-%d %H:%M:%S'
        # when filename is not None, "stream" parameter is ignored (see https://docs.python.org/2/library/logging.html#logging.basicConfig)
        logging.basicConfig(filename=config['log_file'],stream=sys.stdout,level=log_level,format=log_format,datefmt=log_datefmt)
        self.logger = logging.getLogger()
        logger = self.logger

        # define root, template and static directories
        self.root_dir = os.path.dirname(os.path.abspath(__file__)).rstrip(os.sep)
        self.template_dir = self.root_dir + os.sep + 'templates'
        self.static_dir = self.root_dir + os.sep + 'static'

        logger.debug('Root directory: %s',self.root_dir)

        # make sure run and data directories exist
        util.make_sure_path_exists(self.run_dir)
        util.make_sure_path_exists(self.data_dir)

        self.template_loader = FileSystemLoader(searchpath = self.template_dir)
        self.template_env = Environment(loader = self.template_loader)

        self.runs = GSRun.find_runs(self.run_dir)
        self.gene_annotations = GSGeneAnnotation.find_gene_annotations(self.data_dir)
        self.go_annotations = GSGoAnnotation.find_go_annotations(self.data_dir)

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
                'logger': self.logger,\
                'max_file_size': self.max_file_size}

        self.app = tornado.web.Application([
            (r'/static/(.*)$', tornado.web.StaticFileHandler, {'path': self.static_dir}),
            (r'/gopca$', GOPCAHandler,dict(data=data),'submit'),
            (r'/delete-run$', DeleteRunHandler,dict(data=data),'delete-run'),
            (r'/update-gene-annotations$', GeneAnnotationUpdateHandler,dict(data=data),'update-gene-annotations'),
            (r'/update-go-annotations$', GOAnnotationUpdateHandler,dict(data=data),'update-go-annotations'),
            (r'/run/([0-9a-f]{32}/(?:gopca_pipeline_log\.txt|gopca_signature_matrix\.png|gopca_signatures\.tsv|gopca_signatures\.xlsx))$', \
                    tornado.web.StaticFileHandler, {'path': self.run_dir}),
            (r'/run/([0-9a-f]{32})$', RunHandler,dict(data=data),'run'),
            (r'/run/([0-9a-f]{32})/signature/(-?[0-9]+)$', SignatureHandler,dict(data=data),'signature'),
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
    def disk_quota(self):
        return self.config['disk_quota']

    @property
    def max_file_size(self):
        return self.config['max_file_size']

    @property
    def cookie_key(self):
        return self.config['cookie_key']

    @staticmethod
    def get_argument_parser():

        parser = argparse.ArgumentParser(description='GO-PCA Web Server')

        parser.add_argument('-k','--cookie-key',required=True,help='Secret cookie key.')
        parser.add_argument('-r','--run-dir',required=True,help='Directory for storing runs.')
        parser.add_argument('-d','--data-dir',required=True,help='Directory for storing annotation data.')
        parser.add_argument('-p','--port',type=int,default=None,help='Port that the server listens on. If None, default to 80 (HTTP) or 443 (HTTPS).')
        parser.add_argument('--disk-quota',type=float,default=5000.0,help='Maximal disk space to use, in MB.') # currently ignored
        parser.add_argument('--max-file-size',type=float,default=200.0,help='Maximal GO-PCA input size, in MB.') # currently ignored
        parser.add_argument('--species',nargs='+',default=['Homo_sapiens','Mus_musculus'])
        parser.add_argument('--ssl-dir',default=None,help='SSL certificate and private key directory. If not specified, disable SSL.')
        parser.add_argument('--log-file',default=None,help='Log file - if not specified, print to stdout.')
        parser.add_argument('-v','--verbose',action='store_true',help='Verbose output. If --quiet is specified, this is parameter is ignored.')
        parser.add_argument('-q','--quiet',action='store_true',help='Only output errors and warnings. Takes precedence over --verbose.')

        return parser

    def get_config_from_cmdline(self):
        parser = self.get_argument_parser()
        args = parser.parse_args()

        # checks?
        config = {}

        config['run_dir'] = os.path.abspath(args.run_dir).rstrip(os.sep)
        config['data_dir'] = os.path.abspath(args.data_dir).rstrip(os.sep)

        config['ssl_dir'] = None
        ssl_dir = args.ssl_dir
        if ssl_dir is not None:
            assert os.path.isdir(ssl_dir)
            assert os.path.isfile(ssl_dir + os.sep + 'server.cert')
            assert os.path.isfile(ssl_dir + os.sep + 'server.key')
            config['ssl_dir'] = os.path.abspath(ssl_dir).rstrip(os.sep)

        config['port'] = args.port
        if config['port'] is None:
            if config['ssl_dir'] is None:
                config['port'] = 80
            else:
                config['port'] = 443

        config['disk_quota'] = args.disk_quota
        config['max_file_size'] = args.max_file_size
        config['cookie_key'] = args.cookie_key
        config['species'] = sorted(args.species)
        config['log_file'] = os.path.abspath(args.log_file)
        config['verbose'] = args.verbose
        config['quiet'] = args.quiet
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
