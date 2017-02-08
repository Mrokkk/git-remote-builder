#!/bin/env python3

import socket
import logging
from daemons.prefab import run

class Master(run.RunDaemon):

    logger = None
    socket = None
    shell = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.shell = Shell()
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
                    data = self.read_from_connection(connection)
                    if not data:
                        break
                    self.logger.debug('{} sent "{}"'.format(client_address[0], data))
                    self.shell.dispatch(data)
            finally:
                self.logger.info('{} closed connection'.format(client_address[0]))
                connection.close()

    def read_from_connection(self, connection):
        try:
            return connection.recv(1024).strip().decode('ascii')
        except:
            return None


class Shell:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def dispatch(self, data):
        arguments = data.split(' ')
        command = arguments[0]
        arguments = arguments[1:]
        self.logger.info('Command: {} Args: {}'.format(command, arguments))
        pass
