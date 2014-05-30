.. _http-server-api:

********************
HTTP server side API
********************

The :ref:`ext-http` extension comes with an HTTP server to host Mopidy's
:ref:`http-api`. This web server can also be used by other extensions that need
to expose something over HTTP.

The HTTP server side API can be used to:

- host static files for e.g. a Mopidy client written in pure JavaScript,
- host a `Tornado <http://www.tornadoweb.org/>`__ application, or
- host a WSGI application.

To extend the web server, an extension needs to create a subclass of
:class:`mopidy.http.Router` and register the subclass with the extension
registry under the ``http:router`` key.

For details on how to make a Mopidy extension, see the :ref:`extensiondev`
guide.


Static web client example
=========================

To serve static files, you just need to declare a
:attr:`~mopidy.http.Router.name` for your router and tell where the static
files are located by setting the :attr:`~mopidy.http.Router.static_file_path`
attribute on your router class.

The :attr:`~mopidy.http.Router.name` attribute is used to build the URL to
make the files available on. By convention, it should be identical with the
extension's :attr:`~mopidy.ext.Extension.ext_name`, like in the examples here.

Assuming that the code below is located in the file
:file:`mywebclient/__init__.py`, the files in the directory
:file:`mywebclient/static/` will be made available at ``/mywebclient/`` on
Mopidy's web server. For example, :file:`mywebclient/static/foo.html` will be
available at http://localhost:6680/mywebclient/foo.html.

::

    from __future__ import unicode_literals

    import os

    from mopidy import ext, http


    class MyStaticFilesRouter(http.Router):
        name = 'mywebclient'
        static_file_path = os.path.join(os.path.dirname(__file__), 'static')


    class MyWebClientExtension(ext.Extension):
        ext_name = 'mywebclient'

        def setup(self, registry):
            registry.add('http:router', MyStaticFilesRouter)

        # See the Extension API for the full details on this class


Tornado application example
===========================

The :ref:`ext-http` extension's web server is based on the `Tornado
<http://www.tornadoweb.org/>`__ web framework. Thus, it has first class support
for Tornado request handlers.

In the following example, we create a :class:`tornado.web.RequestHandler`
called :class:`MyRequestHandler` that responds to HTTP GET requests with the
string ``Hello, world!``. The router registers this Tornado request handler on
the root URL, ``/``. The URLs returned from
:meth:`~mopidy.http.Router.get_request_handlers` are combined with the
:attr:`~mopidy.http.Router.name`` attribute of the router, so the full absolute
URL for the request handler becomes ``/mywebclient/``.

The router is added to the extension registry by
:meth:`MyWebClientExtension.setup`. When the extension is installed, Mopidy
will respond to requests to http://localhost:6680/mywebclient/ with the string
``Hello, world!``.

::

    from __future__ import unicode_literals

    import os

    import tornado.web

    from mopidy import ext, http


    class MyRequestHandler(tornado.web.RequestHandler):
        def get(self):
            self.write('Hello, world!')


    class MyTornadoRouter(http.Router):
        name = 'mywebclient'

        def get_request_handlers(self):
            return [
                ('/', MyRequestHandler)
            ]


    class MyWebClientExtension(ext.Extension):
        ext_name = 'mywebclient'

        def setup(self, registry):
            registry.add('http:router', MyTornadoRouter)

        # See the Extension API for the full details on this class



WSGI application example
========================

WSGI applications are second-class citizens on Mopidy's HTTP server. The WSGI
applications are run inside Tornado, which is based on non-blocking I/O and a
single event loop. In other words, your WSGI applications will only have a
single thread to run on, and if your application is doing blocking I/O, it will
block all other requests from being handled by the web server as well.

The example below shows how a WSGI application that returns the string
``Hello, world!`` on all requests. The WSGI application is wrapped as a Tornado
application and mounted at http://localhost:6680/mywebclient/.

::

    from __future__ import unicode_literals

    import os

    import tornado.web
    import tornado.wsgi

    from mopidy import ext, http


    class MyWSGIRouter(http.Router):
        name = 'mywebclient'

        def get_request_handlers(self):
            def wsgi_app(environ, start_response):
                status = '200 OK'
                response_headers = [('Content-type', 'text/plain')]
                start_response(status, response_headers)
                return ['Hello, world!\n']

            return [
                ('(.*)', tornado.web.FallbackHandler, {
                    'fallback': tornado.wsgi.WSGIContainer(wsgi_app),
                }),
            ]


    class MyWebClientExtension(ext.Extension):
        ext_name = 'mywebclient'

        def setup(self, registry):
            registry.add('http:router', MyTornadoRouter)

        # See the Extension API for the full details on this class


HTTP Router API
===============

.. autoclass:: mopidy.http.Router
    :members:
