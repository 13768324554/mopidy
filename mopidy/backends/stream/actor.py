from __future__ import unicode_literals

import logging
import urlparse

import pykka

from mopidy import audio as audio_lib, exceptions
from mopidy.audio import scan
from mopidy.backends import base
from mopidy.models import Track

logger = logging.getLogger('mopidy.backends.stream')


class StreamBackend(pykka.ThreadingActor, base.Backend):
    def __init__(self, config, audio):
        super(StreamBackend, self).__init__()

        self.library = StreamLibraryProvider(
            backend=self, timeout=config['stream']['timeout'])
        self.playback = base.BasePlaybackProvider(audio=audio, backend=self)
        self.playlists = None

        self.uri_schemes = audio_lib.supported_uri_schemes(
            config['stream']['protocols'])


class StreamLibraryProvider(base.BaseLibraryProvider):
    def __init__(self, backend, timeout):
        super(StreamLibraryProvider, self).__init__(backend)
        self._scanner = scan.Scanner(min_duration=None, timeout=timeout)

    def lookup(self, uri):
        if urlparse.urlsplit(uri).scheme not in self.backend.uri_schemes:
            return []

        try:
            data = self._scanner.scan(uri)
            track = scan.audio_data_to_track(data)
        except exceptions.ScannerError as e:
            logger.warning('Problem looking up %s: %s', uri, e)
            track = Track(uri=uri, name=uri)

        return [track]
