#!/bin/env python3

import asyncio
import logging

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

