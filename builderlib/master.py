#!/bin/env python3

import sys
import os
import socket
import ssl
import logging
import asyncio
import getpass
import secrets
from base64 import b64encode
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class MasterProtocol(asyncio.Protocol):

    logger = None
    master = None
    transport = None
    peername = None

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
        if not data:
            self.transport.close()
        response = self.master.parse_message(data)
        if not response:
            self.transport.close()
        else:
            self.transport.write(response)


class PostReceiveProtocol(asyncio.Protocol):

    transport = None
    master = None
    logger = None
    peername = None

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
        response = self.master.build_request(data)
        if not response:
            self.transport.close()
        else:
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
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message')
            return None
        response = messages_pb2.Result()
        if not message.token:
            if message.WhichOneof('command') == 'auth':
                self.logger.info('Got authentication request')
                if str(message.auth.password).strip() == str(self.password).strip():
                    self.client_token = secrets.token_hex(16)
                    response.token = self.client_token
                    self.logger.info('Accepted request. Sending token')
                else:
                    self.logger.warning('Denied attempt to authenticate with bad password')
                    response.code = messages_pb2.Result.FAIL
            else:
                self.logger.warning('Message without token. Closing connection')
                return None
        elif message.token == self.client_token:
            self.logger.info('{}: {}'.format(self.msg, MessageToString(message, as_one_line=True)))
            response.code = messages_pb2.Result.OK
        else:
            self.logger.warning('Bad token in the message')
            return None
        return response.SerializeToString()

    def build_request(self, data):
        commit = data.decode('ascii').strip()
        if not commit:
            return None
        self.logger.info('Got build request for commit {}'.format(commit))
        return b'OK'
        # TODO


def configure_logger(filename):
    date_format = '%Y.%m.%d:%H.%M.%S'
    format_string = '[%(asctime)s:%(levelname).1s:%(name)s]: %(message)s'
    logging.basicConfig(format=format_string,
                        datefmt=date_format,
                        filemode='w',
                        filename=filename,
                        level=logging.DEBUG)
    formatter = logging.Formatter(format_string, datefmt=date_format)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.addHandler(console)
    return logger


def main(certfile=None, keyfile=None, port=None):
    os.umask(0o077)
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
    client_coro = loop.create_server(lambda: MasterProtocol(master, logger),
                                     host='127.0.0.1',
                                     port=port,
                                     ssl=ssl_context)
    post_receive_coro = loop.create_server(lambda: PostReceiveProtocol(master, logger),
                                           host='127.0.0.1',
                                           port='8090')
    post_receive_server = loop.run_until_complete(post_receive_coro)
    client_server = loop.run_until_complete(client_coro)
    logger.info('Server running on {}'.format(client_server.sockets[0].getsockname()))
    logger.info('Server running on {}'.format(post_receive_server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('\nInterrupted')
        pass
    finally:
        post_receive_server.close()
        client_server.close()
        loop.close()

