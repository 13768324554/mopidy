from __future__ import unicode_literals

import logging
import os

import tornado.escape
import tornado.web
import tornado.websocket

import mopidy
from mopidy import core, http, models
from mopidy.utils import jsonrpc


logger = logging.getLogger(__name__)


class MopidyHttpRouter(http.Router):
    name = 'mopidy'

    def get_request_handlers(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        return [
            (r'/ws/?', WebSocketHandler, {'core': self.core}),
            (r'/rpc', JsonRpcHandler, {'core': self.core}),
            (r'/(.*)', StaticFileHandler, {
                'path': data_dir, 'default_filename': 'mopidy.html'
            }),
        ]


def make_jsonrpc_wrapper(core_actor):
    inspector = jsonrpc.JsonRpcInspector(
        objects={
            'core.get_uri_schemes': core.Core.get_uri_schemes,
            'core.get_version': core.Core.get_version,
            'core.library': core.LibraryController,
            'core.playback': core.PlaybackController,
            'core.playlists': core.PlaylistsController,
            'core.tracklist': core.TracklistController,
        })
    return jsonrpc.JsonRpcWrapper(
        objects={
            'core.describe': inspector.describe,
            'core.get_uri_schemes': core_actor.get_uri_schemes,
            'core.get_version': core_actor.get_version,
            'core.library': core_actor.library,
            'core.playback': core_actor.playback,
            'core.playlists': core_actor.playlists,
            'core.tracklist': core_actor.tracklist,
        },
        decoders=[models.model_json_decoder],
        encoders=[models.ModelJSONEncoder]
    )


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    # XXX This set is shared by all WebSocketHandler objects. This isn't
    # optimal, but there's currently no use case for having more than one of
    # these anyway.
    clients = set()

    @classmethod
    def broadcast(cls, msg):
        for client in cls.clients:
            client.write_message(msg)

    def initialize(self, core):
        self.jsonrpc = make_jsonrpc_wrapper(core)

    def open(self):
        self.set_nodelay(True)
        self.clients.add(self)
        logger.debug(
            'New WebSocket connection from %s', self.request.remote_ip)

    def on_close(self):
        self.clients.discard(self)
        logger.debug(
            'Closed WebSocket connection from %s',
            self.request.remote_ip)

    def on_message(self, message):
        if not message:
            return

        logger.debug(
            'Received WebSocket message from %s: %r',
            self.request.remote_ip, message)

        try:
            response = self.jsonrpc.handle_json(
                tornado.escape.native_str(message))
            if response and self.write_message(response):
                logger.debug(
                    'Sent WebSocket message to %s: %r',
                    self.request.remote_ip, response)
        except Exception as e:
            logger.error('WebSocket request error:', e)
            self.close()


class JsonRpcHandler(tornado.web.RequestHandler):
    def initialize(self, core):
        self.jsonrpc = make_jsonrpc_wrapper(core)

    def head(self):
        self.set_extra_headers()
        self.finish()

    def post(self):
        data = self.request.body
        if not data:
            return

        logger.debug(
            'Received RPC message from %s: %r', self.request.remote_ip, data)

        try:
            self.set_extra_headers()
            response = self.jsonrpc.handle_json(
                tornado.escape.native_str(data))
            if response and self.write(response):
                logger.debug(
                    'Sent RPC message to %s: %r',
                    self.request.remote_ip, response)
        except Exception as e:
            logger.error('HTTP JSON-RPC request error:', e)
            self.write_error(500)

    def set_extra_headers(self):
        self.set_header('Accept', 'application/json')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header(
            'X-Mopidy-Version', mopidy.__version__.encode('utf-8'))
        self.set_header('Content-Type', 'application/json; utf-8')


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-cache')
        self.set_header(
            'X-Mopidy-Version', mopidy.__version__.encode('utf-8'))
