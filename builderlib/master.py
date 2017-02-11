#!/bin/env python3

import sys
import os
import socket
import logging
import ssl
from . import messages_pb2

class Master:

    logger = None
    port = None
    socket = None
    shell = None
    certfile = None
    keyfile = None

    def __init__(self, certfile=None, keyfile=None, port=None):
        logfile = os.path.join(os.getcwd(), 'log')
        logging.basicConfig(filename=logfile, level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.port = port if port else 0
        self.certfile = certfile
        self.keyfile = keyfile

    def run(self):
        address = 'localhost', self.port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.certfile and self.keyfile:
            self.logger.info('Using SSL')
            self.socket = ssl.wrap_socket(self.socket,
                                          server_side=True,
                                          certfile=self.certfile,
                                          keyfile=self.keyfile)
        self.socket.bind(address)
        address, self.port = self.socket.getsockname()
        self.logger.info('Started server at port {}'.format(self.port))
        print('Started server at port {}'.format(self.port))
        self.socket.listen(1)
        self.serve_forever()

    def serve_forever(self):
        while True:
            connection, client_address = self.socket.accept()
            self.logger.info('{} opened connection'.format(client_address[0]))
            try:
                while True:
                    data = self.read_from_connection(connection)
                    if not data:
                        break
                    self.logger.info('{} sent:\n{}'.format(client_address[0], data))
                    response = messages_pb2.Result()
                    response.code = messages_pb2.Result.OK
                    connection.sendall(response.SerializeToString())
            finally:
                self.logger.info('{} closed connection'.format(client_address[0]))
                connection.close()

    def read_from_connection(self, connection):
        data = connection.recv(1024)
        if not data:
            return None
        msg = messages_pb2.Command()
        msg.ParseFromString(data)
        return msg


def main(certfile=None, keyfile=None, port=None):
    Master(certfile=certfile, keyfile=keyfile, port=port).run()

