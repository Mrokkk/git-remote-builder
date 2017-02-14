#!/bin/env python3

import logging
import asyncio

class Application:

    loop = None
    servers = []
    logger = None

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

    def run(self):
        self.loop.run_forever()

    def stop(self):
        self.logger.info('Stopping application')
        for server in self.servers:
            server.close()
        self.loop.close()
