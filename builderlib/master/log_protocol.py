#!/bin/env python3

import sys
import os
import asyncio
import logging


class LogProtocol(asyncio.Protocol):

    on_open = None
    on_close = None
    on_receive = None

    def __init__(self, log_name, on_close_callback=None):
        self.log_name = log_name
        self.on_close_callback = on_close_callback
        self.on_receive = []
        self.file = open(self.log_name, 'w', buffering=1)
        self.logger = logging.getLogger(self.__class__.__name__ + '.' + self.log_name)
        self.logger.debug('Constructor')

    def set_open_callback(self, callback):
        self.on_open = callback

    def set_close_callback(self, callback):
        self.on_close = callback

    def connection_made(self, transport):
        if self.on_open:
            self.on_open()
        self.file.seek(0)
        self.file.truncate()
        self.peername = transport.get_extra_info('peername')
        self.transport = transport

    def connection_lost(self, exc):
        self.transport.close()
        if self.on_close:
            self.on_close()

    def add_reader(self, reader_func):
        self.logger.info('Adding reader for "{}"'.format(self.log_name))
        self.on_receive.append(reader_func)

    def data_received(self, data):
        self.file.write(data.decode('utf-8'))
        if self.on_receive:
            for callback in self.on_receive:
                try:
                    callback(data)
                except:
                    self.on_receive.remove(callback)