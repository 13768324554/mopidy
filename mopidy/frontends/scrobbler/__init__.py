from __future__ import unicode_literals

import os

import mopidy
from mopidy import exceptions, ext
from mopidy.utils import config


class Extension(ext.Extension):

    dist_name = 'Mopidy-Scrobbler'
    ext_name = 'scrobbler'
    version = mopidy.__version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return open(conf_file).read()

    def get_config_schema(self):
        schema = config.ExtensionConfigSchema()
        schema['username'] = config.String()
        schema['password'] = config.String(secret=True)
        return schema

    def validate_environment(self):
        try:
            import pylast  # noqa
        except ImportError as e:
            raise exceptions.ExtensionError('pylast library not found', e)

    def get_frontend_classes(self):
        from .actor import ScrobblerFrontend
        return [ScrobblerFrontend]
