import pkg_resources

__version__ = pkg_resources.require('gopca-server')[0].version

from gpserver.config import GSConfig
from gpserver.job import GSJob
from gpserver.server import GOPCAServer

__all__ = ['GSConfig', 'GOPCAServer', 'GSJob']
