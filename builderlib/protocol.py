#!/bin/env python3

import asyncio

class Protocol(asyncio.Protocol):

    logger = None
    message_handler = None
    transport = None
    peername = None

    def __init__(self, message_handler, logger):
        self.message_handler = message_handler
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
        response = self.message_handler(data)
        if not response:
            self.transport.close()
        else:
            self.transport.write(response)

