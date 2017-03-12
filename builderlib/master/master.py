#!/bin/env python3

import socket
import logging
from builderlib.message_helpers import create_result
from builderlib import messages_pb2

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
        return create_result(messages_pb2.Result.FAIL, error=error)

    def handle_build_request(self, message, peername):
        self.logger.info('Received new commit {}/{}'.format(message.branch, message.commit_hash))
        self.build_dispatcher.enqueue(message.branch, self.slaves, self.jobs)
        return create_result(messages_pb2.Result.OK)

    def handle_job_adding(self, message, peername):
        try:
            self.validate_job_adding_message(message)
        except RuntimeError as exc:
            return self.error('Error adding job: {}'.format(exc))
        self.logger.info('Adding job: {}'.format(message.name))
        try:
            job = self.job_factory.create_job(message.name, message.script)
        except Exception as exc:
            return self.error('Cannot create job: {}'.format(exc))
        self.jobs.append(job)
        return create_result(messages_pb2.Result.OK)

    def validate_job_adding_message(self, message):
        if not message.name:
            raise RuntimeError('No job name')
        if not message.script:
            raise RuntimeError('No script')

    def handle_connect_slave(self, message, peername):
        address = (message.address, message.port)
        self.logger.info('{}: Connecting slave: {}'.format(peername, address))
        try:
            slave = self.connection_factory.create_connection((message.address, message.port), message.password)
        except Exception as exc:
            return self.error('Error connecting to slave: {}'.format(exc))
        self.slaves.append(slave)
        return create_result(messages_pb2.Result.OK)

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
        return create_result(messages_pb2.Result.OK)
