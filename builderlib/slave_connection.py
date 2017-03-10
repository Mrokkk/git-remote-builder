#!/bin env python3

import logging
from . import messages_pb2


class SlaveConnection:
    connection = None
    token = None
    free = None
    address = None

    def __init__(self, address, password, connection_factory):
        self.logger = logging.getLogger("{}.{}".format(self.__class__.__name__, address))
        self.logger.debug('Constructor')
        self.address = address
        self.free = True
        self.connection = connection_factory(address[0], address[1])
        token_request = messages_pb2.SlaveCommand()
        token_request.auth.password = password
        response = self.connection.send(token_request)
        if not response.token:
            raise RuntimeError('Bad password')
        self.token = response.token

    def set_free(self):
        self.logger.info('Finished build')
        self.free = True

    def set_busy(self):
        self.logger.info('Starting build')
        self.free = False

    def send_build_request(self, repo_address, branch, log_server_port, script):
        message = messages_pb2.SlaveCommand()
        message.token = self.token
        message.build.repo_address = repo_address
        message.build.branch = branch
        message.build.log_server_port = log_server_port
        message.build.script = script
        self.connection.send_nowait(message)


class SlaveConnectionFactory:

    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def create_connection(self, address, password):
        return SlaveConnection(address, password, self.connection_factory)
