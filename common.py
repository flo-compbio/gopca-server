# -*- coding: utf-8 -*-

import os
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
