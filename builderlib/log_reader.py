#!/bin/env python3

import sys
import os
import asyncio
import logging


class LogProtocol(asyncio.Protocol):

    def __init__(self, log_name):
        self.log_name = log_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def connection_made(self, transport):
        self.file = open(self.log_name, 'w')
        self.peername = transport.get_extra_info('peername')
        self.logger.info('{} opened connection'.format(self.peername))
        self.transport = transport

    def connection_lost(self, exc):
        self.logger.info('{} closed connection'.format(self.peername))
        self.file.close()
        self.transport.close()

    def data_received(self, data):
        self.file.write(data.decode('utf-8'))
