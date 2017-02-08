#!/bin/env python3

import socket
import logging
from daemons.prefab import run

class Master(run.RunDaemon):

    logger = None
    socket = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.debug('Constructor')

    def run(self):
        address = 'localhost', 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(address)
        address, self.port = self.socket.getsockname()
        self.logger.info('Started server at port {}'.format(self.port))
        self.socket.listen(1)
        while True:
            connection, client_address = self.socket.accept()
            self.logger.info('{} opened connection'.format(client_address[0]))
            try:
                while True:
                    data = connection.recv(1024).strip()
                    if not data:
                        self.logger.info('{} closed connection'.format(client_address[0]))
                        break
                    self.logger.info('{} sent "{}"'.format(client_address[0], data.decode('ascii')))
            finally:
                connection.close()
