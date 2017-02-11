#!/bin/env python3

import sys
import os
import socket
import ssl
import logging
import asyncio
import getpass
from base64 import b64encode
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class MasterProtocol(asyncio.Protocol):

    logger = None

    def __init__(self, master, logger):
        self.master = master
        self.logger = logger.getChild(self.__class__.__name__)

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        self.logger.info('{} opened connection'.format(self.peername))
        self.transport = transport

    def connection_lost(self, exc):
        self.logger.info('{} closed connection'.format(self.peername))
        self.transport.close()

    def data_received(self, data):
        response = self.master.parse_message(data)
        if not response:
            self.transport.close()
        self.transport.write(response)


class Master:

    msg = 0
    password = None
    logger = None
    slaves = []
    client_token = None

    def __init__(self, password, logger):
        self.password = password
        self.logger = logger.getChild(self.__class__.__name__)
        pass

    def parse_message(self, data):
        self.msg = self.msg + 1
        message = messages_pb2.Command()
        message.ParseFromString(data)
        response = messages_pb2.Result()
        if not message.token:
            if message.WhichOneof('command') == 'auth':
                self.logger.info('Got authentication request')
                if str(message.auth.password).strip() == str(self.password).strip():
                    self.client_token = os.urandom(64)
                    response.token = b64encode(self.client_token)
                    self.logger.info('Accepted request. Sending token')
                else:
                    self.logger.warning('Denied attempt to authenticate with bad password')
                    response.code = messages_pb2.Result.FAIL
            else:
                self.logger.warning('Message without token. Closing connection')
                return None
        else:
            self.logger.info('{}: {}'.format(self.msg, MessageToString(message, as_one_line=True)))
            response.code = messages_pb2.Result.OK
        return response.SerializeToString()


def configure_logger(filename):
    format_string = '[%(asctime)s:%(levelname).1s:%(name)s]: %(message)s'
    logging.basicConfig(format=format_string,
                        filename=filename,
                        level=logging.DEBUG)
    formatter = logging.Formatter(format_string, datefmt="%Y.%m.%d:%H.%M.%S")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.addHandler(console)
    return logger


def main(certfile=None, keyfile=None, port=None):
    password, ssl_context = '', None
    password = getpass.getpass(prompt='Set password: ')
    if password != getpass.getpass(prompt='Vaildate password: '):
        print('Passwords don\'t match!')
        sys.exit(1)
    logger = configure_logger('log')
    master = Master(password, logger)
    password = None
    loop = asyncio.get_event_loop()
    if keyfile and certfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile, keyfile=keyfile)
    coroutine = loop.create_server(lambda: MasterProtocol(master, logger),
                                                          host='127.0.0.1',
                                                          port=port,
                                                          ssl=ssl_context)
    server = loop.run_until_complete(coroutine)
    logger.info('Server running on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('\nInterrupted')
        pass
    finally:
        server.close()
        loop.close()

