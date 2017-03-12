#!/bin/env python3

import logging
from .log_protocol import *


class Job:
    name = None
    log_protocol = None
    script = None
    port = None
    logger = None

    def __init__(self, name, script, server_factory):
        self.logger = logging.getLogger(self.__class__.__name__ + '.' + name)
        self.logger.debug('Constructor')
        self.name = name
        self.script = script
        self.server_factory = server_factory
        self.log_protocol = LogProtocol(name)
        self.port = self.server_factory(lambda: self.log_protocol)

    def __del__(self):
        self.logger.debug('Destructor')

    def add_reader(self, reader):
        self.log_protocol.add_reader(reader)
