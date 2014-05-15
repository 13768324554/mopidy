.. _http-api:

********
HTTP API
********

.. module:: mopidy.http
    :synopsis: The HTTP frontend APIs

The :ref:`ext-http` extension makes Mopidy's :ref:`core-api` available over
HTTP using WebSockets. We also provide a JavaScript wrapper, called
:ref:`Mopidy.js <mopidy-js>` around the HTTP API for use both from browsers and
Node.js.

.. warning:: API stability

    Since the HTTP API exposes our internal core API directly it is to be
    regarded as **experimental**. We cannot promise to keep any form of
    backwards compatibility between releases as we will need to change the core
    API while working out how to support new use cases. Thus, if you use this
    API, you must expect to do small adjustments to your client for every
    release of Mopidy.

    From Mopidy 1.0 and onwards, we intend to keep the core API far more
    stable.


Server side API
===============

TODO: Describe how this is used. Consider splitting this page into multiple
pages.

.. autoclass:: mopidy.http.Router
    :members:


.. _websocket-api:

WebSocket API
=============

The web server exposes a WebSocket at ``/mopidy/ws/``. The WebSocket gives you
access to Mopidy's full API and enables Mopidy to instantly push events to the
client, as they happen.

On the WebSocket we send two different kind of messages: The client can send
JSON-RPC 2.0 requests, and the server will respond with JSON-RPC 2.0 responses.
In addition, the server will send event messages when something happens on the
server. Both message types are encoded as JSON objects.


Event messages
--------------

Event objects will always have a key named ``event`` whose value is the event
type. Depending on the event type, the event may include additional fields for
related data. The events maps directly to the :class:`mopidy.core.CoreListener`
API. Refer to the ``CoreListener`` method names is the available event types.
The ``CoreListener`` method's keyword arguments are all included as extra
fields on the event objects. Example event message::

    {"event": "track_playback_started", "track": {...}}


JSON-RPC 2.0 messaging
----------------------

JSON-RPC 2.0 messages can be recognized by checking for the key named
``jsonrpc`` with the string value ``2.0``. For details on the messaging format,
please refer to the `JSON-RPC 2.0 spec
<http://www.jsonrpc.org/specification>`_.

All methods (not attributes) in the :ref:`core-api` is made available through
JSON-RPC calls over the WebSocket. For example,
:meth:`mopidy.core.PlaybackController.play` is available as the JSON-RPC method
``core.playback.play``.

The core API's attributes is made available through setters and getters. For
example, the attribute :attr:`mopidy.core.PlaybackController.current_track` is
available as the JSON-RPC method ``core.playback.get_current_track``.

Example JSON-RPC request::

    {"jsonrpc": "2.0", "id": 1, "method": "core.playback.get_current_track"}

Example JSON-RPC response::

    {"jsonrpc": "2.0", "id": 1, "result": {"__model__": "Track", "...": "..."}}

The JSON-RPC method ``core.describe`` returns a data structure describing all
available methods. If you're unsure how the core API maps to JSON-RPC, having a
look at the ``core.describe`` response can be helpful.
