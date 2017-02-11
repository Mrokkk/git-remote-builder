#!/bin/env python3

import sys
import os
import socket
import ssl
import logging
from . import messages_pb2
from google.protobuf.text_format import *
import asyncio

class Master:

    port = None
    socket = None
    shell = None
    certfile = None
    keyfile = None
    logger = None

    def __init__(self, certfile=None, keyfile=None, port=None):
        self.port = port if port else 0
        self.certfile = certfile
        self.keyfile = keyfile
        self.configure_log()

    def configure_log(self):
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(format=format_string,
                            filename='log',
                            level=logging.DEBUG)
        formatter = logging.Formatter(format_string)
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(console)

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
                    self.logger.info('{} sent: {}'.format(client_address[0], MessageToString(data, indent=1, as_one_line=True)))
                    response = messages_pb2.Result()
                    response.code = messages_pb2.Result.OK
                    connection.sendall(response.SerializeToString())
            finally:
                self.logger.warning('{} closed connection'.format(client_address[0]))
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

