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
import git
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class Protocol(asyncio.Protocol):

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
            return
        response = self.master.parse_message(data)
        if not response:
            self.transport.close()
        else:
            self.transport.write(response)


class Master:

    msg = 0
    password = None
    repo = None
    logger = None
    slaves = []
    client_token = None

    def __init__(self, password, repo, logger):
        self.password = password
        self.repo = repo
        self.logger = logger.getChild(self.__class__.__name__)
        self.logger.info('Repo at: {}'.format(self.repo.working_dir))
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
            elif message.build and not message.build.script:
                self.logger.info('Received new commit {}'.format(message.build.commit_hash))
                response.code = messages_pb2.Result.OK
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


def main(name, certfile=None, keyfile=None, port=None):
    os.umask(0o077)
    password, ssl_context = '', None
    password = getpass.getpass(prompt='Set password: ')
    if password != getpass.getpass(prompt='Vaildate password: '):
        print('Passwords don\'t match!')
        sys.exit(1)
    logger = configure_logger('log')
    master = Master(password, git.Repo.init(os.path.join(os.getcwd(), name), bare=True), logger)
    password = None
    loop = asyncio.get_event_loop()
    if keyfile and certfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile, keyfile=keyfile)
    client_coro = loop.create_server(lambda: Protocol(master, logger),
                                     host='127.0.0.1',
                                     port=port,
                                     ssl=ssl_context)
    post_receive_coro = loop.create_server(lambda: Protocol(master, logger),
                                           host='127.0.0.1',
                                           port='8090')
    post_receive_server = loop.run_until_complete(post_receive_coro)
    client_server = loop.run_until_complete(client_coro)
    logger.info('Main server running on {}'.format(client_server.sockets[0].getsockname()))
    logger.info('Post-receive server running on {}'.format(post_receive_server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('\nInterrupted')
        pass
    finally:
        post_receive_server.close()
        client_server.close()
        loop.close()

