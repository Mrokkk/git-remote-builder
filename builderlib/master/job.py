#!/bin/env python3

import logging
from .log_protocol import *
from .log_reader import *


class Job:

    name = None
    log_protocol = None
    script = None
    port = None
    logger = None

    def __init__(self, name, script, port, log_protocol):
        self.logger = logging.getLogger(self.__class__.__name__ + '.' + name)
        self.name = name
        self.script = script
        self.port = port
        self.log_protocol = log_protocol
        self.log_reader = LogReader(name)
        self.log_protocol.add_reader(lambda data: self.log_reader.reader_callback(data))
        self.logger.debug('Constructor')

    def add_reader(self, reader):
        self.log_protocol.add_reader(reader)


class JobFactory:

    def __init__(self, server_factory):
        self.server_factory = server_factory

    def create_job(self, name, script):
        log_protocol = LogProtocol(name)
        port = self.server_factory(lambda: log_protocol)
        return Job(name, script, port, log_protocol)
