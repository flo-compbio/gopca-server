# -*- coding: utf-8 -*-

import sys
import os
import errno
import urllib2
import logging
from contextlib import closing
from collections import Counter

from genometools import misc

from items import *

def get_logger(name = '', log_stream = sys.stdout, log_file = None,
    quiet = False, verbose = False):

    # configure root logger
    log_level = logging.INFO
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG

    new_logger = misc.configure_logger(name, log_stream, log_file, log_level)

    return new_logger

def download_url(url,output_file):
    with closing(urllib2.urlopen(url)) as uh, open(output_file,'wb') as ofh:
        ofh.write(uh.read())

def read_url(url):
    body = None
    with closing(urllib2.urlopen(url)) as uh:
        body = uh.read()
    return body

def make_sure_path_exists(path):
    """ Make sure a path exists.

    Source: http://stackoverflow.com/a/5032238
    Authors: StackOverflow users "Heikko Toivono" (http://stackoverflow.com/users/62596/heikki-toivonen) 
            and "Bengt" (http://stackoverflow.com/users/906658/bengt)
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
