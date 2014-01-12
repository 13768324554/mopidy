.. _backend-api:

***********
Backend API
***********

.. module:: mopidy.backend
    :synopsis: The API implemented by backends

The backend API is the interface that must be implemented when you create a
backend. If you are working on a frontend and need to access the backends, see
the :ref:`core-api` instead.


URIs and routing of requests to the backend
===========================================

When Mopidy's core layer is processing a client request, it routes the request
to one or more appropriate backends based on the URIs of the objects the
request touches on. The objects' URIs are compared with the backends'
:attr:`~mopidy.backend.Backend.uri_scheme` to select the relevant backends.

An often used pattern when implementing Mopidy backends is to create your own
URI scheme which you use for all tracks, playlists, etc. related to your
backend. For example:

- Spotify already got an URI scheme (``spotify:track:...``,
  ``spotify:playlist:...``, etc.) used throughout their applications, and thus
  Mopidy-Spotify simply use the same URI scheme.

- Mopidy-Soundcloud created it's own URI scheme, after the model of Spotify,
  and use URIs of the following forms: ``soundcloud:search``,
  ``soundcloud:user-...``, ``soundcloud:exp-...``, and ``soundcloud:set-...``.

- Mopidy differentiates between ``file://...`` URIs handled by
  :ref:`ext-stream` and ``local:...`` URIs handled by :ref:`ext-local`.
  :ref:`ext-stream` can play ``file://...`` URIs to tracks and playlists
  located anywhere on your system, but it doesn't know a thing about the
  object before you play it. On the other hand, :ref:`ext-local` scans a
  predefined :confval:`local/media_dir` to build a metadata library of all
  known tracks. It is thus limited to playing tracks residing in the media
  library, but can provide additional features like directory browsing and
  search. In other words, we got two different ways of playing local music,
  handled by two different backends, and have thus created to different URI
  schemes to separate their handling.

If there isn't an existing URI scheme that fits for your backend's purpose,
you should create your own, and name it after your extension's
:attr:`~mopidy.ext.Extension.ext_name`.


Backend class
=============

.. autoclass:: mopidy.backend.Backend
    :members:


Playback provider
=================

.. autoclass:: mopidy.backend.PlaybackProvider
    :members:


Playlists provider
==================

.. autoclass:: mopidy.backend.PlaylistsProvider
    :members:


Library provider
================

.. autoclass:: mopidy.backend.LibraryProvider
    :members:


Backend listener
================

.. autoclass:: mopidy.backend.BackendListener
    :members:


.. _backend-implementations:

Backend implementations
=======================

- `Mopidy-Beets <https://github.com/mopidy/mopidy-beets>`_

- `Mopidy-GMusic <https://github.com/hechtus/mopidy-gmusic>`_

- :ref:`ext-local`

- `Mopidy-radio-de <https://github.com/hechtus/mopidy-radio-de>`_

- `Mopidy-SomaFM <https://github.com/AlexandrePTJ/mopidy-somafm>`_

- `Mopidy-SoundCloud <https://github.com/mopidy/mopidy-soundcloud>`_

- `Mopidy-Spotify <https://github.com/mopidy/mopidy-spotify>`_

- :ref:`ext-stream`

- `Mopidy-Subsonic <https://github.com/rattboi/mopidy-subsonic>`_

- `Mopidy-VKontakte <https://github.com/sibuser/mopidy-vkontakte>`_
