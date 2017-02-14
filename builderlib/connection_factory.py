#!/bin/env python3

import socket

class ConnectionFactory:

    def __init__(self, ssl_context=None):
        self.ssl_context = ssl_context

    def create(self, hostname, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.ssl_context:
            sock = self.ssl_context.wrap_socket(sock, server_side=False)
        address = (hostname, port)
        sock.connect(address)
        sock.settimeout(10)
        return sock

