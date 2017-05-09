#!/bin/env python3

import asyncio

class LogProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        print('Got connection!')
        self.peername = transport.get_extra_info('peername')
        self.transport = transport

    def connection_lost(self, exc):
        print('Lost connection!')
        self.transport.close()

    def data_received(self, data):
        print(data.decode('utf-8'), end='', flush=True)
