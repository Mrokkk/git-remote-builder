#!/bin/env python3

import sys
import os
import time
import socketserver
import logging
from daemons.prefab import run

class Handler(socketserver.BaseRequestHandler):

    def handle(self):
        LOG = logging.getLogger('Handler.handle')
        while True:
            try:
                self.data = self.request.recv(1024).strip()
                if not self.data:
                    return
                LOG.debug('{} wrote: {}'.format(self.client_address[0], self.data.decode('ascii')))
                self.request.sendto(b'OK\n', self.client_address)
            except:
                return


class Serverd(run.RunDaemon):

    def run(self):
        host, port = 'localhost', 8090
        LOG = logging.getLogger('Serverd.run')
        with socketserver.TCPServer((host, port), Handler) as server:
            LOG.info('Serving at port {}'.format(port))
            server.serve_forever()
