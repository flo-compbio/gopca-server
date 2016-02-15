#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

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

"""Script to run a tornado-based GO-PCA web server."""

import os
import textwrap

from gpserver import cli
from gpserver import util
from gpserver import GSConfig
from gpserver import GOPCAServer

def get_argument_parser():

    desc = 'Start the GO-PCA Server'
    parser = cli.get_argument_parser(desc = desc)

    #cli.add_server_args(parser)

    #g.add_argument('-k','--cookie-key',required=True,help='Secret cookie key.')

    str_type = cli.str_type
    file_mv = cli.file_mv
    dir_mv = cli.dir_mv
    int_mv = cli.int_mv
    float_mv = cli.float_mv

    g = parser.add_argument_group('Server configuration')

    defaults = GSConfig.param_defaults

    g.add_argument('-p', '--port', type = int, default = defaults['port'],
            metavar = int_mv, help = textwrap.dedent("""\
                Port that the server listens on.
                If unspecified, defaults to 80 (HTTP) or 443 (HTTPS)."""))

    g.add_argument('-d', '--data-dir', required = True, type = str_type,
            metavar = dir_mv,
            help = 'Directory for storing annotation data.')

    g.add_argument('-j', '--job-dir', required = True, type = str_type,
            metavar = dir_mv,
            help = 'Directory for storing GO-PCA jobs.')

    g.add_argument('-s', '--ssl-dir', type = str_type,
            default = defaults['ssl_dir'], metavar = dir_mv,
            help = textwrap.dedent("""\
                SSL certificate and private key directory.
                If not specified, SSL is disabled."""))

    g.add_argument('--disk-quota', type = float,
            default = defaults['disk_quota'], metavar = float_mv,
            help = 'Maximal disk space for run data, in MB.') # ignored

    g.add_argument('--max-file-size', type = float,
            default = defaults['max_file_size'], metavar = float_mv,
            help = 'Maximal GO-PCA input size, in MB.') # ignored

    g.add_argument('--species', type = str_type, nargs = '+',
            default = defaults['species'], help = 'List of supported species.')

    g.add_argument('--seed', type = int, default = defaults['seed'],
            metavar = int_mv, help = textwrap.dedent("""\
                'Seed for the random number generator.
                 If not specified, an arbitrary seed is used."""))

    cli.add_reporting_args(parser)

    return parser

def main(args = None):

    if args is None:
        parser = get_argument_parser()
        args = parser.parse_args()

    # directory parameters
    data_dir = os.path.abspath(args.data_dir).rstrip(os.sep)
    job_dir = os.path.abspath(args.job_dir).rstrip(os.sep)
    ssl_dir = args.ssl_dir
    if ssl_dir is not None:
        ssl_dir = os.path.abspath(ssl_dir).rstrip(os.sep)

    # other server parameters
    port = args.port
    disk_quota = args.disk_quota
    max_file_size = args.max_file_size
    #cookie_key = args.cookie_key
    species = sorted(args.species)
    seed = args.seed

    # reporting parameters
    log_file = args.log_file
    if log_file is not None:
        log_file = os.path.abspath(log_file)
    quiet = args.quiet
    verbose = args.verbose

    # configure root logger
    logger = util.get_logger(log_file = log_file, quiet = quiet,
            verbose = verbose)

    # create GO-PCA Server configuration
    params = {}
    for p in sorted(GSConfig.param_names):
        params[p] = locals()[p]

    config = GSConfig(params)

    server = GOPCAServer(config)
    server.run()

    return 0

if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)
