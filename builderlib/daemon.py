#!/bin/env python3

import logging
import socketserver
from daemons.prefab import run

class ServerDaemon(run.RunDaemon):

    __handler = None

    def __init__(self, handler, *args, **kwargs):
        self.__handler = handler
        super().__init__(*args, **kwargs)

    def run(self):
        host, port = 'localhost', 0
        logger = logging.getLogger(__name__)
        with socketserver.TCPServer((host, port), self.__handler) as server:
            logger.info('Serving at {}'.format(server.server_address))
            server.serve_forever()
