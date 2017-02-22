#!/bin/env python3

import sys
import os
import asyncio
import logging
from application import *


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


def main():
    log_name = sys.argv[1]
    logging.basicConfig(filemode='w',
                        filename='log_log',
                        level=logging.DEBUG)
    app = Application()
    port = app.create_server(lambda: LogProtocol(log_name), 0)
    print(port)
    sys.stdout.flush()
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == '__main__':
    main()
