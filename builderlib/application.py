#!/bin/env python3

import logging
import asyncio
import threading
from .connection import *


class Application:

    loop = None
    server_ssl_context = None
    client_ssl_context = None
    servers = []
    logger = None
    condition = threading.Condition()
    port = None

    def __init__(self, server_ssl_context=None, client_ssl_context=None):
        self.server_ssl_context = server_ssl_context
        self.client_ssl_context = client_ssl_context
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_server(self, proto, port, ssl=True):
        ssl_context = self.server_ssl_context if ssl else None
        coro = self.loop.create_server(proto, host='127.0.0.1', port=port, ssl=ssl_context)
        server = self.loop.run_until_complete(coro)
        self.servers.append(server)
        self.logger.info('Created server at {}'.format(server.sockets[0].getsockname()))
        return server.sockets[0].getsockname()[1]

    def __server_thread(self, proto):
        loop = asyncio.new_event_loop()
        coro = loop.create_server(proto, host='127.0.0.1', port=0)
        server = loop.run_until_complete(coro)
        self.condition.acquire()
        self.port = server.sockets[0].getsockname()[1]
        self.condition.notify()
        self.condition.release()
        loop.run_forever()

    def create_connection(self, hostname, port):
        return Connection((hostname, port), self.client_ssl_context)

    def create_task(self, func):
        self.loop.run_in_executor(None, func)

    def create_server_thread(self, proto):
        self.port = None
        threading.Thread(target=self.__server_thread, args=(proto, ), daemon=True).start()
        self.condition.acquire()
        self.condition.wait(timeout=10)
        self.condition.release()
        self.logger.info('Created server at {}'.format(self.port))
        return self.port

    def run(self):
        self.loop.run_forever()

    def stop(self):
        self.logger.info('Stopping application')
        for server in self.servers:
            server.close()
        self.loop.close()
