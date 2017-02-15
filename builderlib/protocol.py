#!/bin/env python3

import asyncio
import logging

class Protocol(asyncio.Protocol):

    logger = None
    message_handler = None
    transport = None
    peername = None

    def __init__(self, message_handler):
        self.message_handler = message_handler
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

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
            self.logger.warning('No data from message handler. Closing.')
            self.transport.close()
        else:
            self.transport.write(response)

