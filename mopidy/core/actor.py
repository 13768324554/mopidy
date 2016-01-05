from __future__ import absolute_import, unicode_literals

import collections
import itertools
import logging
import os

import pykka

from mopidy import audio, backend, mixer
from mopidy.audio import PlaybackState
from mopidy.core.history import HistoryController
from mopidy.core.library import LibraryController
from mopidy.core.listener import CoreListener
from mopidy.core.mixer import MixerController
from mopidy.core.playback import PlaybackController
from mopidy.core.playlists import PlaylistsController
from mopidy.core.tracklist import TracklistController
from mopidy.internal import versioning
from mopidy.internal.deprecation import deprecated_property
from mopidy.models import storage


logger = logging.getLogger(__name__)


class Core(
        pykka.ThreadingActor, audio.AudioListener, backend.BackendListener,
        mixer.MixerListener):

    library = None
    """An instance of :class:`~mopidy.core.LibraryController`"""

    history = None
    """An instance of :class:`~mopidy.core.HistoryController`"""

    mixer = None
    """An instance of :class:`~mopidy.core.MixerController`"""

    playback = None
    """An instance of :class:`~mopidy.core.PlaybackController`"""

    playlists = None
    """An instance of :class:`~mopidy.core.PlaylistsController`"""

    tracklist = None
    """An instance of :class:`~mopidy.core.TracklistController`"""

    def __init__(self, config=None, mixer=None, backends=None, audio=None):
        super(Core, self).__init__()

        self._config = config

        self.backends = Backends(backends)

        self.library = LibraryController(backends=self.backends, core=self)
        self.history = HistoryController()
        self.mixer = MixerController(mixer=mixer)
        self.playback = PlaybackController(
            audio=audio, backends=self.backends, core=self)
        self.playlists = PlaylistsController(backends=self.backends, core=self)
        self.tracklist = TracklistController(core=self)

        self.audio = audio

    def get_uri_schemes(self):
        """Get list of URI schemes we can handle"""
        futures = [b.uri_schemes for b in self.backends]
        results = pykka.get_all(futures)
        uri_schemes = itertools.chain(*results)
        return sorted(uri_schemes)

    uri_schemes = deprecated_property(get_uri_schemes)
    """
    .. deprecated:: 1.0
        Use :meth:`get_uri_schemes` instead.
    """

    def get_version(self):
        """Get version of the Mopidy core API"""
        return versioning.get_version()

    version = deprecated_property(get_version)
    """
    .. deprecated:: 1.0
        Use :meth:`get_version` instead.
    """

    def reached_end_of_stream(self):
        self.playback._on_end_of_stream()

    def stream_changed(self, uri):
        self.playback._on_stream_changed(uri)

    def position_changed(self, position):
        self.playback._on_position_changed(position)

    def state_changed(self, old_state, new_state, target_state):
        # XXX: This is a temporary fix for issue #232 while we wait for a more
        # permanent solution with the implementation of issue #234. When the
        # Spotify play token is lost, the Spotify backend pauses audio
        # playback, but mopidy.core doesn't know this, so we need to update
        # mopidy.core's state to match the actual state in mopidy.audio. If we
        # don't do this, clients will think that we're still playing.

        # We ignore cases when target state is set as this is buffering
        # updates (at least for now) and we need to get #234 fixed...
        if (new_state == PlaybackState.PAUSED and not target_state and
                self.playback.state != PlaybackState.PAUSED):
            self.playback.state = new_state
            self.playback._trigger_track_playback_paused()

    def playlists_loaded(self):
        # Forward event from backend to frontends
        CoreListener.send('playlists_loaded')

    def volume_changed(self, volume):
        # Forward event from mixer to frontends
        CoreListener.send('volume_changed', volume=volume)

    def mute_changed(self, mute):
        # Forward event from mixer to frontends
        CoreListener.send('mute_changed', mute=mute)

    def tags_changed(self, tags):
        if not self.audio or 'title' not in tags:
            return

        tags = self.audio.get_current_tags().get()
        if not tags:
            return

        # TODO: this limits us to only streams that set organization, this is
        # a hack to make sure we don't emit stream title changes for plain
        # tracks. We need a better way to decide if something is a stream.
        if 'title' in tags and tags['title'] and 'organization' in tags:
            title = tags['title'][0]
            self.playback._stream_title = title
            CoreListener.send('stream_title_changed', title=title)

    def on_start(self):
        logger.debug("core on_start")
        try:
            coverage = []
            if self._config and 'restore_state' in self._config['core']:
                amount = self._config['core']['restore_state']
                if not amount or 'off' == amount:
                    pass
                elif 'volume' == amount:
                    coverage = ['volume']
                elif 'load' == amount:
                    coverage = ['tracklist', 'mode', 'volume', 'history']
                elif 'last' == amount:
                    coverage = ['tracklist', 'mode', 'play-last', 'volume',
                                'history']
                elif 'play' == amount:
                    coverage = ['tracklist', 'mode', 'play-always', 'volume',
                                'history']
                else:
                    logger.warn('Unknown value for config '
                                'core.restore_state: %s', amount)
            if len(coverage):
                self.load_state('persistent', coverage)
        except Exception as e:
            logger.warn('Unexpected error: %s', str(e))
        pykka.ThreadingActor.on_start(self)

    def on_stop(self):
        logger.debug("core on_stop")
        try:
            if self._config and 'restore_state' in self._config['core']:
                amount = self._config['core']['restore_state']
                if amount and 'off' != amount:
                    self.save_state('persistent')
        except Exception as e:
            logger.warn('on_stop: Unexpected error: %s', str(e))
        pykka.ThreadingActor.on_stop(self)

    def save_state(self, name):
        """
        Save current state to disk.

        :param name: a name (for later use with :meth:`load_state`)
        :type name: str
        """
        if not name:
            raise TypeError('missing file name')

        file_name = os.path.join(
            self._config['core']['data_dir'], name)
        file_name += '.state'
        logger.info('Save state to %s', file_name)

        data = {}
        data['tracklist'] = self.tracklist._export_state()
        data['history'] = self.history._export_state()
        data['playback'] = self.playback._export_state()
        data['mixer'] = self.mixer._export_state()
        storage.save(file_name, data)
        logger.debug('Save state done')

    def load_state(self, name, coverage):
        """
        Restore state from disk.

        Load state from disk and restore it. Parameter `coverage`
        limits the amount data to restore. Possible
        values for `coverage` (list of one or more of):

            - 'tracklist' fill the tracklist
            - 'mode' set tracklist properties (consume, random, repeat, single)
            - 'autoplay' start playing ('tracklist' also required)
            - 'volume' set mixer volume
            - 'history' restore history

        :param name: a name (used previously with :meth:`save_state`)
        :type path: str
        :param coverage: amount of data to restore
        :type coverage: list of string (see above)
        """
        if not name:
            raise TypeError('missing file name')

        file_name = os.path.join(
            self._config['core']['data_dir'], name)
        file_name += '.state'
        logger.info('Load state from %s', file_name)

        data = storage.load(file_name)
        if 'history' in data:
            self.history._restore_state(data['history'], coverage)
        if 'tracklist' in data:
            self.tracklist._restore_state(data['tracklist'], coverage)
        if 'playback' in data:
            # playback after tracklist
            self.playback._restore_state(data['playback'], coverage)
        if 'mixer' in data:
            self.mixer._restore_state(data['mixer'], coverage)
        logger.debug('Load state done.')


class Backends(list):

    def __init__(self, backends):
        super(Backends, self).__init__(backends)

        self.with_library = collections.OrderedDict()
        self.with_library_browse = collections.OrderedDict()
        self.with_playback = collections.OrderedDict()
        self.with_playlists = collections.OrderedDict()

        backends_by_scheme = {}

        def name(b):
            return b.actor_ref.actor_class.__name__

        for b in backends:
            try:
                has_library = b.has_library().get()
                has_library_browse = b.has_library_browse().get()
                has_playback = b.has_playback().get()
                has_playlists = b.has_playlists().get()
            except Exception:
                self.remove(b)
                logger.exception('Fetching backend info for %s failed',
                                 b.actor_ref.actor_class.__name__)

            for scheme in b.uri_schemes.get():
                assert scheme not in backends_by_scheme, (
                    'Cannot add URI scheme "%s" for %s, '
                    'it is already handled by %s'
                ) % (scheme, name(b), name(backends_by_scheme[scheme]))
                backends_by_scheme[scheme] = b

                if has_library:
                    self.with_library[scheme] = b
                if has_library_browse:
                    self.with_library_browse[scheme] = b
                if has_playback:
                    self.with_playback[scheme] = b
                if has_playlists:
                    self.with_playlists[scheme] = b
