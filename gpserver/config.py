# Copyright (c) 2015 Florian Wagner, Razvan Panea
#
# This file is part of GO-PCA Server.
#
# GO-PCA Sever is free software: you can redistribute it and/or modify
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

"""Module containing the GSConfig class.

"""

import os
import hashlib
import logging
#from ConfigParser import SafeConfigParser

import numpy as np

from genometools import misc

logger = logging.getLogger(__name__)

class GSConfig(object):
    """GO-PCA Server configuration class.

    """

    ### static members
    param_defaults = {
        'port': None,
        'ssl_dir': None,
        'disk_quota': 5000.0,
        'max_file_size': 200.0,
        'species': ['Homo_sapiens', 'Mus_musculus'],
        'seed': None,
    }
    """GO-PCA Server parameter default values."""

    dir_param_names = set([
        'data_dir',
        'job_dir',
    ])

    param_names = set(param_defaults.keys()) | dir_param_names
    """Names of all GO-PCA Server parameters."""
    ### end static members

    def __init__(self, params = {}):
        self.__params = {}
        # first, set all parameters to their default values
        self.reset_params()
        # then, set specified parameters to the given values
        self.set_params(params)

    def __getattr__(self, name):
        """Look up attribute in `__params` if it is a GO-PCA Server parameter.

        Note: This function is only called for non-existing attributes.
        """
        if name in self.param_names:
            return self.__params[name]
        else:
            raise AttributeError('There is no GO-PCA parameter called "%s"!' \
                    %(name))

    def __repr__(self):
        return '<GSConfig object (hash=%d)>' %(hash(self))

    def __str__(self):
        param_str = '; '.join(self.get_param_strings())
        return '<GSConfig object (%s)>' %(param_str)

    def __hash__(self):
        return hash(frozenset(self.__params.items()))

    def __deepcopy__(self, memo):
        cp = GSConfig()
        cp.set_params(self.__params)
        return cp

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        else:
            return repr(self) == repr(other)

    ### public members  
    def has_param(self, name):
        """Tests if a GO-PCA Server parameter exists.

        Parameters
        ----------
        name: str
            The name of the parameter.

        Returns
        -------
        bool
            Whether or not the parameter exists.
        """
        return name in self.param_names

    def get_param(self, name):
        """Returns the value of a GO-PCA Server parameter.

        Parameters
        ----------
        name: str
            The name of the parameter.
        
        Returns
        -------
        ?
            The parameter value.
        """
        return self.__params[name]

    def get_param_strings(self):
        d = []
        for k in sorted(self.__params.keys()):
            d.append('%s=%s' %(k,str(self.__params[k])))
        return d

    def get_dict(self):
        """Returns the GO-PCA configuration as a dictionary.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            The configuration.
        """
        return self.__params.copy()

    def set_param(self, name, value):
        """Set a GO-PCA Server parameter.

        Parameters
        ----------
        name: str
            The parameter name.
        value: ?
            The parameter value.
        """
        if name not in self.param_names:
            raise ValueError('No GO-PCA Server parameter named "%s"!' %(param))
        self.__params[name] = value

    def set_params(self, params):
        """Sets multiple GO-PCA Server parameters using a dictionary.

        Parameters
        ----------
        params: dict
            Dictionary containing the parameter values.

        Returns
        -------
        None
        """
        for k,v in params.iteritems():
            self.set_param(k,v)

    def reset_params(self):
        """Reset all parameters to their default values."""
        self.__params = dict([p, None] for p in self.param_names)
        self.set_params(self.param_defaults)

    def check(self):
        """Check if the current configuration is valid.

        Parameters:
        -----------
        None

        Returns
        -------
        bool
            True iff no problems were found.

        """

        passed = True

        def check_type(attr, types):
            # checks whether the parameter has a certain type
            val = getattr(self, attr)
            if not isinstance(val, types):
                logger.error('Parameter "%s" = %s: invalid type ' +
                        '(should be %s).', attr, val, str(types))
                passed = False

        def check_file_exists(attr):
            # check whether the specified file exists
            path = getattr(self, attr)
            if not os.path.isfile(path):
                logger.error('Parameter "%s" = %s: file does not exist. ',
                        attr, path)
                passed = False

        def check_dir_exists(attr):
            # check whether the specified directory exists
            path = getattr(self, attr)
            if not os.path.isdir(path):
                logger.error('Parameter "%s" = %s: directory does not exist.',
                        attr, path)
                passed = False

        def check_dir_writable(attr):
            path = getattr(self, attr)
            if not misc.test_dir_writable(path):
                logger.error('Parameter "%s" = %s: directory is not writable',
                        attr, path)
                passed = False

        def check_file_writable(attr):
            # check whether the specified file is writable
            path = getattr(self, attr)
            if not misc.test_file_writable(path):
                logger.error('Parameter "%s" = %s: file not writable.',
                        attr, path)
                passed = False

        def check_range(attr, mn = None, mx = None,
                left_open = False, right_open = False):
            # checks if a GO-PCA parameter falls within a certain numeric range

            val = getattr(self, attr)
            in_range = True

            rel_op = {True: '<', False: '<='}

            if mn is not None:
                left_rel = '%s %s ' %(str(mn), rel_op[left_open])
                if left_open:
                    if not mn < val: in_range = False
                else:
                    if not mn <= val: in_range = False

            if mx is not None:
                right_rel = ' %s %s' %(rel_op[right_open], str(mx))
                if right_open:
                    if not val < mx: in_range = False
                else:
                    if not val <= mx: in_range = False

            if not in_range:
                logger.error('Parameter "%s" = %s: out of range ' +
                        '(should be %s %s %s).',
                        attr, val, left_rel, attr, right_rel)
                passed = False

        # check if input files are strings
        # specification of gene ontology file is optional
        check_type('data_dir', (str, unicode))
        check_dir_writable('data_dir')

        check_type('job_dir', (str, unicode))
        check_dir_writable('job_dir')

        if self.ssl_dir is not None:
            check_dir_exists('ssl_dir')
            if not os.path.isfile(ssl_dir + os.sep + 'gopca_server.cert'):
                logger.error('SSL certificate file not found!')
                passed = False
            if not os.path.isfile(ssl_dir + os.sep + 'gopca_server.key'):
                logger.error('SSL key file no found!')
                passed = False

        check_type('port', int)

        # TO-DO: check remaining parameters
        return passed

    def read_config_file(self, path):
        raise NotImplemented

    def write_config_file(self, output_file):
        raise NotImplemented
