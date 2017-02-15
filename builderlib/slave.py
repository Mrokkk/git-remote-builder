#!/bin/env python3

import sys
import os
import ssl
import logging
import getpass
import string
import socket
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .utils import *
from google.protobuf.text_format import MessageToString


class Slave:

    repo_address = None
    logger = None

    def __init__(self, auth_handler):
        self.auth_handler = auth_handler
        self.messages_handler = MessagesHandler(
            {
                'auth': self.handle_authentication_request,
                'build': self.handle_build_request
            },
            messages_pb2.SlaveCommand)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_protocol(self):
        return Protocol(lambda data: self.messages_handler.handle(data))

    def handle_authentication_request(self, message):
        response = messages_pb2.Result()
        self.logger.info('Got authentication request')
        token = self.auth_handler.request_token(message.auth.password)
        if token:
            response.token = token
        else:
            self.logger.warning('Denied attempt to authenticate with bad password')
            response.code = messages_pb2.Result.FAIL
        return response

    def handle_build_request(self, message):
        response = messages_pb2.Result()
        self.logger.info('Received new commit {}'.format(message.build.commit_hash))
        if message.build.script:
            self.logger.info('Got script')
            response.code = messages_pb2.Result.OK
        else:
            self.logger.warning('Fuck you')
            response.code = messages_pb2.Result.FAIL
        return response

    def handle_user_request(self, message):
        response = messages_pb2.Result()
        if self.auth_handler.authenticate(message.token):
            self.logger.info('{}'.format(MessageToString(message, as_one_line=True)))
            response.code = messages_pb2.Result.OK
            return response
        else:
            return None


def read_password():
    password = ''
    password = getpass.getpass(prompt='Set password: ')
    if password != getpass.getpass(prompt='Vaildate password: '):
        print('Passwords don\'t match!')
        sys.exit(1)
    return password


def main(name, certfile=None, keyfile=None, port=None):
    app = Application()
    slave = Slave(AuthenticationManager(read_password()))
    app.create_server(slave.create_protocol, port, ssl_context=create_server_ssl_context(certfile, keyfile))
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()
