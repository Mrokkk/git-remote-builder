#!/bin/env python3

import socket
from .messages_pb2 import Result


class Connection:

    sock = None

    def __init__(self, address, ssl_context=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if ssl_context:
            self.sock = ssl_context.wrap_socket(self.sock, server_side=False)
        self.sock.connect(address)
        self.sock.settimeout(10)

    def send(self, message):
        self.sock.sendall(message.SerializeToString())
        data = self.sock.recv(1024)
        result = Result()
        result.ParseFromString(data)
        return result
