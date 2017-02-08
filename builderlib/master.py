#!/bin/env python3

import sys
import os
import time
import socketserver
import logging
from builderlib.connection import WorkerConnection

class RequestHandler(socketserver.BaseRequestHandler):

    __logger = None

    def __init__(self, *args, **kwargs):
        self.__logger = logging.getLogger(__name__)
        self.__logger.debug("Constructor")
        super().__init__(*args, **kwargs)

    def handle(self):
        try:
            con = WorkerConnection(('localhost', 8080))
        except:
            self.__logger.error('Cannot conect to worker')
            return
        self.__logger.info('Connected to worker')
        while True:
            self.data = self.request.recv(1024).strip()
            if not self.data:
                return
            self.__logger.debug('{} wrote: {}'.format(self.client_address[0], self.data.decode('ascii')))
            con.send(self.data)
            self.request.sendto(b'OK\n', self.client_address)
