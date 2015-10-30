# -*- coding: utf-8 -*-

import os
import errno
import urllib2
from contextlib import closing
from collections import Counter

from items import *

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
