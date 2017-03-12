#!/bin/env python3

import sys
import logging
import string
import socket
import subprocess
import pathlib
from builderlib import messages_pb2
from builderlib.message_helpers import create_result
from builderlib.utils import *
from builderlib.protocol import *
from builderlib.authentication import *
from builderlib.messages_handler import *
from builderlib.application import *
from .job import *
from .build_dispatcher import *
from .slave_connection import *
from google.protobuf.text_format import MessageToString


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


def create_post_receive_hook(repo, builderlib_root, port, token):
    hook_path = repo / 'hooks' / 'post-receive'
    path = builderlib_root / 'builderlib' / 'master' / 'post-receive.py'
    template_string = path.open(mode='r').read()
    with hook_path.open(mode='w') as f:
        f.write(string.Template(template_string)
            .substitute(PATH='\'' + str(builderlib_root) + '\'', PORT=port, TOKEN='\'' + token + '\''))
    hook_path.chmod(0o700)


def create_bare_repo(name):
    repo_path =  pathlib.Path.cwd() / (name + '.git')
    repo_path.mkdir(exist_ok=True)
    proc = subprocess.Popen(['git', 'init', '--bare'], cwd=str(repo_path))
    proc.wait()
    return repo_path


def create_master_message_handler(master, auth_manager):
    messages_handler = MessagesHandler(messages_pb2.MasterCommand, auth_manager)
    messages_handler.register_handler('build', master.handle_build_request)
    messages_handler.register_handler('connect_slave', master.handle_connect_slave)
    messages_handler.register_handler('create_job', master.handle_job_adding)
    messages_handler.register_handler('subscribe_job', master.handle_subscribe_job)
    return messages_handler


def main(name, certfile=None, keyfile=None, port=None, jobs=None, slaves=None):
    app = Application(server_ssl_context=create_server_ssl_context(certfile, keyfile),
                      client_ssl_context=create_client_ssl_context(certfile, keyfile))
    repo = create_bare_repo(name)
    build_dispatcher = BuildDispatcher(socket.gethostname() + ':' + str(repo))
    build_dispatcher.start()
    slave_connection_factory = SlaveConnectionFactory(app.create_connection)
    job_factory = JobFactory(app.create_server_thread)
    master = Master(job_factory, slave_connection_factory, build_dispatcher)
    password = read_password(validate=True)
    auth_manager = AuthenticationManager(password)
    messages_handler = create_master_message_handler(master, auth_manager)
    protocol = Protocol(messages_handler.handle)
    app.create_server(lambda: protocol, port)
    git_hook_port = app.create_server(lambda: protocol, 0, ssl=False)
    create_post_receive_hook(repo, pathlib.Path.cwd().parent,
        git_hook_port, auth_manager.request_token(password))
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
