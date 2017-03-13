#!/bin/env python3

import socket
import logging
from . import message_validators
from builderlib.message_helpers import fail_message, success_message

class Master:

    jobs = None
    slaves = None
    server_factory = None
    logger = None

    def __init__(self, job_factory, slave_connection_factory, build_dispatcher):
        self.jobs = []
        self.slaves = []
        self.job_factory = job_factory
        self.connection_factory = slave_connection_factory
        self.build_dispatcher = build_dispatcher
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def error(self, error):
        self.logger.error(error)
        return fail_message(error)

    def handle_build_request(self, message, peername):
        self.logger.info('Received new commit {}/{}'.format(message.branch, message.commit_hash))
        self.build_dispatcher.enqueue(message.branch, self.slaves, self.jobs)
        return success_message()

    @message_validators.create_job
    def handle_job_adding(self, message, peername):
        try:
            self.logger.info('Adding job: {}'.format(message.name))
            job = self.job_factory.create_job(message.name, message.script)
            self.jobs.append(job)
            return success_message()
        except Exception as exc:
            return self.error('Error adding job: {}'.format(exc))

    @message_validators.connect_slave
    def handle_connect_slave(self, message, peername):
        address = (message.address, message.port)
        self.logger.info('{}: Connecting slave: {}'.format(peername, address))
        try:
            slave = self.connection_factory.create_connection((message.address, message.port), message.password)
            self.slaves.append(slave)
            return success_message()
        except Exception as exc:
            return self.error('Error connecting to slave: {}'.format(exc))

    def handle_subscribe_job(self, message, peername):
        try:
            job = next(j for j in self.jobs if j.name == message.name)
        except:
            return self.error('No such job')
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((peername[0], message.port))
        except Exception as exc:
            return self.error('Error connecting to client: {}'.format(exc))
        self.logger.info('{}:{} subscribed for job {}'.format(peername[0], message.port, job.name))
        job.add_reader(self.sock.sendall)
        return success_message()
