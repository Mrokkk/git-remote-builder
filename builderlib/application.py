#!/bin/env python3

import logging
import asyncio
import threading


class Application:

    loop = None
    servers = []
    logger = None
    threads = []
    condition = threading.Condition()
    port = None

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_server(self, proto, port, ssl_context=None):
        coro = self.loop.create_server(proto, host='127.0.0.1', port=port, ssl=ssl_context)
        server = self.loop.run_until_complete(coro)
        self.servers.append(server)
        self.logger.info('Created server at {}'.format(server.sockets[0].getsockname()))
        return server.sockets[0].getsockname()[1]

    def server_thread(self, proto):
        loop = asyncio.new_event_loop()
        coro = loop.create_server(proto, host='127.0.0.1', port=0)
        server = loop.run_until_complete(coro)
        self.port = server.sockets[0].getsockname()[1]
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
        loop.run_forever()

    def create_server_thread(self, proto):
        self.port = None
        t = threading.Thread(target=self.server_thread, args=(proto, ), daemon=True)
        t.start()
        self.threads.append(t)
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
