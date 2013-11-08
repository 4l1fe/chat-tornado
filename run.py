import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tornadochat.settings")
import django.conf
import django.core.handlers.wsgi
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.wsgi
from tornadochat.settings import TORNADO_HOST, TORNADO_PORT
from chat_app.tornadoapp import ChatSocketHandler


def run():
    wsgi_app = tornado.wsgi.WSGIContainer(
        django.core.handlers.wsgi.WSGIHandler())
    tornado_app = tornado.web.Application(
        [
            (r'/websocket', ChatSocketHandler),
            (r'.*', tornado.web.FallbackHandler, dict(fallback=wsgi_app)),
        ])
    server = tornado.httpserver.HTTPServer(tornado_app)
    server.listen(TORNADO_PORT, TORNADO_HOST)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run()
