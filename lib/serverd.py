#!/bin/env python3

import sys
import os
import time
import socketserver
import logging
from daemons.prefab import run
from lib.connection import WorkerConnection

class Handler(socketserver.BaseRequestHandler):

    def handle(self):
        logger = logging.getLogger(__name__)
        con = WorkerConnection(('localhost', 8080))
        while True:
            self.data = self.request.recv(1024).strip()
            if not self.data:
                return
            logger.debug('{} wrote: {}'.format(self.client_address[0], self.data.decode('ascii')))
            con.send(self.data)
            self.request.sendto(b'OK\n', self.client_address)


class ServerDaemon(run.RunDaemon):

    def run(self):
        host, port = 'localhost', 0
        logger = logging.getLogger(__name__)
        with socketserver.TCPServer((host, port), Handler) as server:
            logger.info('Serving at {}'.format(server.server_address))
            server.serve_forever()
