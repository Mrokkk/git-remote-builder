#!/bin/env python3

import socket
import asyncio
import logging
from .messages_pb2 import Result


class Connection:

    sock = None

    def __init__(self, address, ssl_context=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if ssl_context:
            self.sock = ssl_context.wrap_socket(self.sock, server_side=False)
        self.sock.connect(address)
        self.sock.settimeout(10)
        self.logger = logging.getLogger(self.__class__.__name__)

    def __del__(self):
        if self.sock:
            self.sock.close()

    def file(self, mode):
        self.sock.setblocking(True)
        return self.sock.makefile(mode)

    def send(self, message):
        self.sock.sendall(message.SerializeToString())
        data = self.sock.recv(1024)
        if not data:
            raise RuntimeError("Server closed connection!")
        result = Result()
        try:
            result.ParseFromString(data)
        except:
            raise RuntimeError("Bad response!")
        if result.code == Result.FAIL:
            raise RuntimeError("Fail on server side!")
        return result

    def error(self, error):
        self.logger.error(error)
        self.sock.close()

    def dummy_read(self):
        data = self.sock.recv(1024)
        if not data:
            return self.error('Cannot read result from server')
        result = Result()
        try:
            result.ParseFromString(data)
        except:
            return self.error('Bad result message read from the server')
        if result.code == Result.FAIL:
            return self.error('Fail on server side!')

    def send_nowait(self, message):
        self.sock.sendall(message.SerializeToString())
        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
        loop.run_in_executor(None, self.dummy_read)
