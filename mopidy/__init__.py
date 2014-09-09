from __future__ import unicode_literals

import platform
import sys
import warnings
from distutils.version import StrictVersion as SV

import pykka


if not (2, 7) <= sys.version_info < (3,):
    sys.exit(
        'ERROR: Mopidy requires Python 2.7, but found %s.' %
        platform.python_version())

if (isinstance(pykka.__version__, basestring)
        and not SV('1.1') <= SV(pykka.__version__) < SV('2.0')):
    sys.exit(
        'ERROR: Mopidy requires Pykka >= 1.1, < 2, but found %s.' %
        pykka.__version__)


warnings.filterwarnings('ignore', 'could not open display')


__version__ = '0.19.4'
