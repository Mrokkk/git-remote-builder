#!/bin/env python3

import sys
import os
import socket
import ssl
import logging
import asyncio
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class MasterProtocol(asyncio.Protocol):

    shell = None
    certfile = None
    keyfile = None
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
        self.master.msg = self.master.msg + 1
        msg = messages_pb2.Command()
        msg.ParseFromString(data)
        self.logger.info('{} sent {}: {}'.format(self.peername, self.master.msg, MessageToString(msg, as_one_line=True)))
        response = messages_pb2.Result()
        response.code = messages_pb2.Result.OK
        self.transport.write(response.SerializeToString())


class Master:

    msg = 0

    def __init__(self):
        pass



def main(certfile=None, keyfile=None, port=None):
    master = Master()
    ssl_context = None
    loop = asyncio.get_event_loop()
    format_string = '[%(asctime)s:%(levelname).1s:%(name)s]: %(message)s'
    logging.basicConfig(format=format_string,
                        filename='log',
                        level=logging.DEBUG)
    formatter = logging.Formatter(format_string, datefmt="%Y.%m.%d:%H.%M.%S")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.addHandler(console)
    if keyfile and certfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile, keyfile=keyfile)
    coroutine = loop.create_server(lambda: MasterProtocol(master, logger),
                                                          host='127.0.0.1',
                                                          port=port,
                                                          ssl=ssl_context)
    server = loop.run_until_complete(coroutine)
    logger.info('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()

