#!/bin/env python3

import sys
import os
import time
import socket
import logging
from base64 import b64decode, b64encode

class WorkerConnection:

    sock = None

    def __init__(self, worker_address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(worker_address)

    def __del__(self):
        self.sock.close()

    def send(self, data):
        self.sock.sendall(b64encode(data) + b'\n')
