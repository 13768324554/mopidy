from __future__ import absolute_import, unicode_literals

import logging
import urlparse

from mopidy import models
from mopidy.audio import PlaybackState
from mopidy.core import listener
from mopidy.internal import deprecation, validation

logger = logging.getLogger(__name__)


class PlaybackController(object):
    pykka_traversable = True

    def __init__(self, audio, backends, core):
        # TODO: these should be internal
        self.backends = backends
        self.core = core
        self._audio = audio

        self._stream_title = None
        self._state = PlaybackState.STOPPED

        self._current_tl_track = None
        self._pending_tl_track = None

        if self._audio:
            self._audio.set_about_to_finish_callback(self._on_about_to_finish)

    def _get_backend(self, tl_track):
        if tl_track is None:
            return None
        uri_scheme = urlparse.urlparse(tl_track.track.uri).scheme
        return self.backends.with_playback.get(uri_scheme, None)

    # Properties

    def get_current_tl_track(self):
        """Get the currently playing or selected track.

        Returns a :class:`mopidy.models.TlTrack` or :class:`None`.
        """
        return self._current_tl_track

    def _set_current_tl_track(self, value):
        """Set the currently playing or selected track.

        *Internal:* This is only for use by Mopidy's test suite.
        """
        self._current_tl_track = value

    current_tl_track = deprecation.deprecated_property(get_current_tl_track)
    """
    .. deprecated:: 1.0
        Use :meth:`get_current_tl_track` instead.
    """

    def get_current_track(self):
        """
        Get the currently playing or selected track.

        Extracted from :meth:`get_current_tl_track` for convenience.

        Returns a :class:`mopidy.models.Track` or :class:`None`.
        """
        return getattr(self.get_current_tl_track(), 'track', None)

    current_track = deprecation.deprecated_property(get_current_track)
    """
    .. deprecated:: 1.0
        Use :meth:`get_current_track` instead.
    """

    def get_current_tlid(self):
        """
        Get the currently playing or selected TLID.

        Extracted from :meth:`get_current_tl_track` for convenience.

        Returns a :class:`int` or :class:`None`.

        .. versionadded:: 1.1
        """
        return getattr(self.get_current_tl_track(), 'tlid', None)

    def get_stream_title(self):
        """Get the current stream title or :class:`None`."""
        return self._stream_title

    def get_state(self):
        """Get The playback state."""

        return self._state

    def set_state(self, new_state):
        """Set the playback state.

        Must be :attr:`PLAYING`, :attr:`PAUSED`, or :attr:`STOPPED`.

        Possible states and transitions:

        .. digraph:: state_transitions

            "STOPPED" -> "PLAYING" [ label="play" ]
            "STOPPED" -> "PAUSED" [ label="pause" ]
            "PLAYING" -> "STOPPED" [ label="stop" ]
            "PLAYING" -> "PAUSED" [ label="pause" ]
            "PLAYING" -> "PLAYING" [ label="play" ]
            "PAUSED" -> "PLAYING" [ label="resume" ]
            "PAUSED" -> "STOPPED" [ label="stop" ]
        """
        validation.check_choice(new_state, validation.PLAYBACK_STATES)

        (old_state, self._state) = (self.get_state(), new_state)
        logger.debug('Changing state: %s -> %s', old_state, new_state)

        self._trigger_playback_state_changed(old_state, new_state)

    state = deprecation.deprecated_property(get_state, set_state)
    """
    .. deprecated:: 1.0
        Use :meth:`get_state` and :meth:`set_state` instead.
    """

    def get_time_position(self):
        """Get time position in milliseconds."""
        backend = self._get_backend(self.get_current_tl_track())
        if backend:
            return backend.playback.get_time_position().get()
        else:
            return 0

    time_position = deprecation.deprecated_property(get_time_position)
    """
    .. deprecated:: 1.0
        Use :meth:`get_time_position` instead.
    """

    def get_volume(self):
        """
        .. deprecated:: 1.0
            Use :meth:`core.mixer.get_volume()
            <mopidy.core.MixerController.get_volume>` instead.
        """
        deprecation.warn('core.playback.get_volume')
        return self.core.mixer.get_volume()

    def set_volume(self, volume):
        """
        .. deprecated:: 1.0
            Use :meth:`core.mixer.set_volume()
            <mopidy.core.MixerController.set_volume>` instead.
        """
        deprecation.warn('core.playback.set_volume')
        return self.core.mixer.set_volume(volume)

    volume = deprecation.deprecated_property(get_volume, set_volume)
    """
    .. deprecated:: 1.0
        Use :meth:`core.mixer.get_volume()
        <mopidy.core.MixerController.get_volume>` and
        :meth:`core.mixer.set_volume()
        <mopidy.core.MixerController.set_volume>` instead.
    """

    def get_mute(self):
        """
        .. deprecated:: 1.0
            Use :meth:`core.mixer.get_mute()
            <mopidy.core.MixerController.get_mute>` instead.
        """
        deprecation.warn('core.playback.get_mute')
        return self.core.mixer.get_mute()

    def set_mute(self, mute):
        """
        .. deprecated:: 1.0
            Use :meth:`core.mixer.set_mute()
            <mopidy.core.MixerController.set_mute>` instead.
        """
        deprecation.warn('core.playback.set_mute')
        return self.core.mixer.set_mute(mute)

    mute = deprecation.deprecated_property(get_mute, set_mute)
    """
    .. deprecated:: 1.0
        Use :meth:`core.mixer.get_mute()
        <mopidy.core.MixerController.get_mute>` and
        :meth:`core.mixer.set_mute()
        <mopidy.core.MixerController.set_mute>` instead.
    """

    # Methods

    def _on_end_of_stream(self):
        self.set_state(PlaybackState.STOPPED)
        self._set_current_tl_track(None)
        # TODO: self._trigger_track_playback_ended?

    def _on_stream_changed(self, uri):
        self._stream_title = None
        if self._pending_tl_track:
            self._set_current_tl_track(self._pending_tl_track)
            self._pending_tl_track = None
            self._trigger_track_playback_started()

    def _on_about_to_finish(self):
        # TODO: check that we always have a current track
        original_tl_track = self.get_current_tl_track()
        next_tl_track = self.core.tracklist.eot_track(original_tl_track)

        # TODO: only set pending if we have a backend that can play it?
        # TODO: skip tracks that don't have a backend?
        self._pending_tl_track = next_tl_track
        backend = self._get_backend(next_tl_track)

        if backend:
            backend.playback.change_track(next_tl_track.track).get()

        self.core.tracklist._mark_played(original_tl_track)

    def _on_tracklist_change(self):
        """
        Tell the playback controller that the current playlist has changed.

        Used by :class:`mopidy.core.TracklistController`.
        """
        if not self.core.tracklist.tl_tracks:
            self.stop()
            self._set_current_tl_track(None)
        elif self.get_current_tl_track() not in self.core.tracklist.tl_tracks:
            self._set_current_tl_track(None)

    def next(self):
        """
        Change to the next track.

        The current playback state will be kept. If it was playing, playing
        will continue. If it was paused, it will still be paused, etc.
        """
        original_tl_track = self.get_current_tl_track()
        next_tl_track = self.core.tracklist.next_track(original_tl_track)

        backend = self._get_backend(next_tl_track)
        self._set_current_tl_track(next_tl_track)

        if backend:
            backend.playback.prepare_change()
            backend.playback.change_track(next_tl_track.track)

            if self.get_state() == PlaybackState.PLAYING:
                result = backend.playback.play().get()
            elif self.get_state() == PlaybackState.PAUSED:
                result = backend.playback.pause().get()
            else:
                result = True

            if result and self.get_state() != PlaybackState.PAUSED:
                self._trigger_track_playback_started()
            elif not result:
                self.core.tracklist._mark_unplayable(next_tl_track)
                # TODO: can cause an endless loop for single track repeat.
                self.next()
        else:
            self.stop()

        self.core.tracklist._mark_played(original_tl_track)

    def pause(self):
        """Pause playback."""
        backend = self._get_backend(self.get_current_tl_track())
        if not backend or backend.playback.pause().get():
            # TODO: switch to:
            # backend.track(pause)
            # wait for state change?
            self.set_state(PlaybackState.PAUSED)
            self._trigger_track_playback_paused()

    def play(self, tl_track=None, tlid=None):
        """
        Play the given track, or if the given tl_track and tlid is
        :class:`None`, play the currently active track.

        Note that the track **must** already be in the tracklist.

        :param tl_track: track to play
        :type tl_track: :class:`mopidy.models.TlTrack` or :class:`None`
        :param tlid: TLID of the track to play
        :type tlid: :class:`int` or :class:`None`
        """
        if sum(o is not None for o in [tl_track, tlid]) > 1:
            raise ValueError('At most one of "tl_track" and "tlid" may be set')

        tl_track is None or validation.check_instance(tl_track, models.TlTrack)
        tlid is None or validation.check_integer(tlid, min=0)

        if tl_track:
            deprecation.warn('core.playback.play:tl_track_kwarg', pending=True)

        self._play(tl_track=tl_track, tlid=tlid, on_error_step=1)

    def _play(self, tl_track=None, tlid=None, on_error_step=1):
        if tl_track is None and tlid is not None:
            for tl_track in self.core.tracklist.get_tl_tracks():
                if tl_track.tlid == tlid:
                    break
            else:
                tl_track = None

        if tl_track is None:
            if self.get_state() == PlaybackState.PAUSED:
                return self.resume()

            if self.get_current_tl_track() is not None:
                tl_track = self.get_current_tl_track()
            else:
                if on_error_step == 1:
                    tl_track = self.core.tracklist.next_track(tl_track)
                elif on_error_step == -1:
                    tl_track = self.core.tracklist.previous_track(tl_track)

            if tl_track is None:
                return

        assert tl_track in self.core.tracklist.get_tl_tracks()

        # TODO: switch to:
        # backend.play(track)
        # wait for state change?

        if self.get_state() == PlaybackState.PLAYING:
            self.stop()

        self._set_current_tl_track(tl_track)
        self.set_state(PlaybackState.PLAYING)
        backend = self._get_backend(tl_track)
        success = False

        if backend:
            backend.playback.prepare_change()
            try:
                success = (
                    backend.playback.change_track(tl_track.track).get() and
                    backend.playback.play().get())
            except TypeError:
                logger.error(
                    '%s needs to be updated to work with this '
                    'version of Mopidy.',
                    backend.actor_ref.actor_class.__name__)
                logger.debug('Backend exception', exc_info=True)

        if success:
            self.core.tracklist._mark_playing(tl_track)
            self.core.history._add_track(tl_track.track)
            # TODO: replace with stream-changed
            self._trigger_track_playback_started()
        else:
            self.core.tracklist._mark_unplayable(tl_track)
            if on_error_step == 1:
                # TODO: can cause an endless loop for single track repeat.
                self.next()
            elif on_error_step == -1:
                self.previous()

    def previous(self):
        """
        Change to the previous track.

        The current playback state will be kept. If it was playing, playing
        will continue. If it was paused, it will still be paused, etc.
        """
        original_tl_track = self.get_current_tl_track()
        prev_tl_track = self.core.tracklist.previous_track(original_tl_track)

        backend = self._get_backend(prev_tl_track)
        self._set_current_tl_track(prev_tl_track)

        if backend:
            backend.playback.prepare_change()
            # TODO: check return values of change track
            backend.playback.change_track(prev_tl_track.track)
            if self.get_state() == PlaybackState.PLAYING:
                result = backend.playback.play().get()
            elif self.get_state() == PlaybackState.PAUSED:
                result = backend.playback.pause().get()
            else:
                result = True

            if result and self.get_state() != PlaybackState.PAUSED:
                self._trigger_track_playback_started()
            elif not result:
                self.core.tracklist._mark_unplayable(prev_tl_track)
                self.previous()

        # TODO: no return value?

    def resume(self):
        """If paused, resume playing the current track."""
        if self.get_state() != PlaybackState.PAUSED:
            return
        backend = self._get_backend(self.get_current_tl_track())
        if backend and backend.playback.resume().get():
            self.set_state(PlaybackState.PLAYING)
            # TODO: trigger via gst messages
            self._trigger_track_playback_resumed()
        # TODO: switch to:
        # backend.resume()
        # wait for state change?

    def seek(self, time_position):
        """
        Seeks to time position given in milliseconds.

        :param time_position: time position in milliseconds
        :type time_position: int
        :rtype: :class:`True` if successful, else :class:`False`
        """
        # TODO: seek needs to take pending tracks into account :(
        validation.check_integer(time_position)

        if time_position < 0:
            logger.debug(
                'Client seeked to negative position. Seeking to zero.')
            time_position = 0

        if not self.core.tracklist.tracks:
            return False

        if self.current_track and self.current_track.length is None:
            return False

        if self.get_state() == PlaybackState.STOPPED:
            self.play()

        if time_position < 0:
            time_position = 0
        elif time_position > self.current_track.length:
            # TODO: gstreamer will trigger a about to finish for us, use that?
            self.next()
            return True

        backend = self._get_backend(self.get_current_tl_track())
        if not backend:
            return False

        success = backend.playback.seek(time_position).get()
        if success:
            self._trigger_seeked(time_position)
        return success

    def stop(self):
        """Stop playing."""
        if self.get_state() != PlaybackState.STOPPED:
            backend = self._get_backend(self.get_current_tl_track())
            time_position_before_stop = self.get_time_position()
            if not backend or backend.playback.stop().get():
                self.set_state(PlaybackState.STOPPED)
                self._trigger_track_playback_ended(time_position_before_stop)

    def _trigger_track_playback_paused(self):
        logger.debug('Triggering track playback paused event')
        if self.current_track is None:
            return
        listener.CoreListener.send(
            'track_playback_paused',
            tl_track=self.get_current_tl_track(),
            time_position=self.get_time_position())

    def _trigger_track_playback_resumed(self):
        logger.debug('Triggering track playback resumed event')
        if self.current_track is None:
            return
        listener.CoreListener.send(
            'track_playback_resumed',
            tl_track=self.get_current_tl_track(),
            time_position=self.get_time_position())

    def _trigger_track_playback_started(self):
        # TODO: replace with stream-changed
        logger.debug('Triggering track playback started event')
        if self.get_current_tl_track() is None:
            return

        tl_track = self.get_current_tl_track()
        self.core.tracklist._mark_playing(tl_track)
        self.core.history._add_track(tl_track.track)
        listener.CoreListener.send('track_playback_started', tl_track=tl_track)

    def _trigger_track_playback_ended(self, time_position_before_stop):
        logger.debug('Triggering track playback ended event')
        if self.get_current_tl_track() is None:
            return
        listener.CoreListener.send(
            'track_playback_ended',
            tl_track=self.get_current_tl_track(),
            time_position=time_position_before_stop)

    def _trigger_playback_state_changed(self, old_state, new_state):
        logger.debug('Triggering playback state change event')
        listener.CoreListener.send(
            'playback_state_changed',
            old_state=old_state, new_state=new_state)

    def _trigger_seeked(self, time_position):
        logger.debug('Triggering seeked event')
        listener.CoreListener.send('seeked', time_position=time_position)
