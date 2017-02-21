#!/bin/env python3

import sys
import os
import ssl
import logging
import string
import socket
import asyncio
from application import *


class LogProtocol(asyncio.Protocol):

    def __init__(self):
        pass

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        self.transport = transport

    def connection_lost(self, exc):
        self.transport.close()

    def data_received(self, data):
        pass


def main():
    app = Application()
    port = app.create_server(LogProtocol(), 0)
    print(port)
    sys.stdout.flush()
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == '__main__':
    main()
