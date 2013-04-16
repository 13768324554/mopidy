from __future__ import unicode_literals

import platform

import pygst
pygst.require('0.10')
import gst

import mock
import pykka

try:
    import dbus
except ImportError:
    dbus = False

try:
    import pylast
except ImportError:
    pylast = False

try:
    import serial
except ImportError:
    serial = False

try:
    import spotify
except ImportError:
    spotify = False

try:
    import cherrypy
except ImportError:
    cherrypy = False

try:
    import ws4py
except ImportError:
    ws4py = False

from mopidy.utils import deps

from tests import unittest


class DepsTest(unittest.TestCase):
    def test_format_dependency_list(self):
        adapters = [
            lambda: dict(name='Python', version='FooPython 2.7.3'),
            lambda: dict(name='Platform', version='Loonix 4.0.1'),
            lambda: dict(
                name='Pykka', version='1.1',
                path='/foo/bar/baz.py', other='Quux'),
            lambda: dict(name='Foo'),
            lambda: dict(name='Mopidy', version='0.13', dependencies=[
                dict(name='pylast', version='0.5', dependencies=[
                    dict(name='setuptools', version='0.6')
                ])
            ])
        ]

        result = deps.format_dependency_list(adapters)

        self.assertIn('Python: FooPython 2.7.3', result)

        self.assertIn('Platform: Loonix 4.0.1', result)

        self.assertIn('Pykka: 1.1 from /foo/bar', result)
        self.assertNotIn('/baz.py', result)
        self.assertIn('Detailed information: Quux', result)

        self.assertIn('Foo: not found', result)

        self.assertIn('Mopidy: 0.13', result)
        self.assertIn('  pylast: 0.5', result)
        self.assertIn('    setuptools: 0.6', result)

    def test_platform_info(self):
        result = deps.platform_info()

        self.assertEquals('Platform', result['name'])
        self.assertIn(platform.platform(), result['version'])

    def test_python_info(self):
        result = deps.python_info()

        self.assertEquals('Python', result['name'])
        self.assertIn(platform.python_implementation(), result['version'])
        self.assertIn(platform.python_version(), result['version'])
        self.assertIn('python', result['path'])

    def test_gstreamer_info(self):
        result = deps.gstreamer_info()

        self.assertEquals('GStreamer', result['name'])
        self.assertEquals(
            '.'.join(map(str, gst.get_gst_version())), result['version'])
        self.assertIn('gst', result['path'])
        self.assertIn('Python wrapper: gst-python', result['other'])
        self.assertIn(
            '.'.join(map(str, gst.get_pygst_version())), result['other'])
        self.assertIn('Relevant elements:', result['other'])

    def test_pykka_info(self):
        result = deps.pykka_info()

        self.assertEquals('Pykka', result['name'])
        self.assertEquals(pykka.__version__, result['version'])
        self.assertIn('pykka', result['path'])

    @unittest.skipUnless(spotify, 'pyspotify not found')
    def test_pyspotify_info(self):
        result = deps.pyspotify_info()

        self.assertEquals('pyspotify', result['name'])
        self.assertEquals(spotify.__version__, result['version'])
        self.assertIn('spotify', result['path'])
        self.assertIn('Built for libspotify API version', result['other'])
        self.assertIn(str(spotify.api_version), result['other'])

    @unittest.skipUnless(pylast, 'pylast not found')
    def test_pylast_info(self):
        result = deps.pylast_info()

        self.assertEquals('pylast', result['name'])
        self.assertEquals(pylast.__version__, result['version'])
        self.assertIn('pylast', result['path'])

    @unittest.skipUnless(dbus, 'dbus not found')
    def test_dbus_info(self):
        result = deps.dbus_info()

        self.assertEquals('dbus-python', result['name'])
        self.assertEquals(dbus.__version__, result['version'])
        self.assertIn('dbus', result['path'])

    @unittest.skipUnless(serial, 'serial not found')
    def test_serial_info(self):
        result = deps.serial_info()

        self.assertEquals('pyserial', result['name'])
        self.assertEquals(serial.VERSION, result['version'])
        self.assertIn('serial', result['path'])

    @unittest.skipUnless(cherrypy, 'cherrypy not found')
    def test_cherrypy_info(self):
        result = deps.cherrypy_info()

        self.assertEquals('cherrypy', result['name'])
        self.assertEquals(cherrypy.__version__, result['version'])
        self.assertIn('cherrypy', result['path'])

    @unittest.skipUnless(ws4py, 'ws4py not found')
    def test_ws4py_info(self):
        result = deps.ws4py_info()

        self.assertEquals('ws4py', result['name'])
        self.assertEquals(ws4py.__version__, result['version'])
        self.assertIn('ws4py', result['path'])

    @mock.patch('pkg_resources.get_distribution')
    def test_pkg_info(self, get_distribution_mock):
        dist_mopidy = mock.Mock()
        dist_mopidy.project_name = 'Mopidy'
        dist_mopidy.version = '0.13'
        dist_mopidy.location = '/tmp/example/mopidy'
        dist_mopidy.requires.return_value = ['Pykka']

        dist_pykka = mock.Mock()
        dist_pykka.project_name = 'Pykka'
        dist_pykka.version = '1.1'
        dist_pykka.location = '/tmp/example/pykka'
        dist_pykka.requires.return_value = ['setuptools']

        dist_setuptools = mock.Mock()
        dist_setuptools.project_name = 'setuptools'
        dist_setuptools.version = '0.6'
        dist_setuptools.location = '/tmp/example/setuptools'
        dist_setuptools.requires.return_value = []

        get_distribution_mock.side_effect = [
            dist_mopidy, dist_pykka, dist_setuptools]

        result = deps.pkg_info()

        self.assertEquals('Mopidy', result['name'])
        self.assertEquals('0.13', result['version'])
        self.assertIn('mopidy', result['path'])

        dep_info_pykka = result['dependencies'][0]
        self.assertEquals('Pykka', dep_info_pykka['name'])
        self.assertEquals('1.1', dep_info_pykka['version'])

        dep_info_setuptools = dep_info_pykka['dependencies'][0]
        self.assertEquals('setuptools', dep_info_setuptools['name'])
        self.assertEquals('0.6', dep_info_setuptools['version'])
