#!/bin/env python3

import sys
import os
import ssl
import logging
import string
import socket
import git
import subprocess
import threading
import time
from . import messages_pb2
from .message_helpers import create_result
from .utils import *
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .log_reader import LogProtocol
from google.protobuf.text_format import MessageToString


class Master:

    repo_address = None
    jobs = []
    slaves = []
    clients = []
    logger = None

    def __init__(self, auth_handler, repo_address, jobs, slaves, client_ssl_context, server_factory):
        self.auth_handler = auth_handler
        self.repo_address = repo_address
        if jobs:
            self.jobs = jobs
        if slaves:
            self.slaves = slaves
        self.messages_handler = MessagesHandler(messages_pb2.MasterCommand, self.auth_handler)
        self.messages_handler.register_handler('build', self.handle_build_request, require_auth=False)
        self.messages_handler.register_handler('connect_slave', self.handle_connect_slave)
        self.messages_handler.register_handler('create_job', self.handle_job_adding)
        self.client_ssl_context = client_ssl_context
        self.server_factory = server_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_protocol(self):
        return Protocol(self.messages_handler.handle)

    def handle_build_request(self, message, peername):
        self.logger.info('Received new commit {}/{}'.format(message.branch, message.commit_hash))
        message_to_slave = self.create_slave_build_request(message.branch)
        sock = self.slaves[0][0]
        sock.send(message_to_slave.SerializeToString())
        return create_result(messages_pb2.Result.OK)

    def create_slave_build_request(self, branch):
        # TODO
        message = messages_pb2.SlaveCommand()
        message.token = self.slaves[0][1]
        message.build.repo_address = os.path.abspath('repo.git')
        message.build.branch = branch
        message.build.log_server_port = self.jobs[0][2]
        with open(self.jobs[0][1]) as f:
            message.build.script = f.read().encode('ascii')
        return message

    def handle_job_adding(self, message, peername):
        error = self.validate_job_adding_message(message)
        if error:
            return error
        self.logger.info('Adding job: {} with script {}'.format(message.name,
            message.script_path))
        port = self.server_factory(lambda: LogProtocol(message.name))
        if not port:
            return create_result(messages_pb2.Result.FAIL, error='Cannot start log server')
        self.jobs.append(
            (message.name, os.path.abspath(message.script_path), port))
        return create_result(messages_pb2.Result.OK)

    def validate_job_adding_message(self, message):
        if not message.name:
            self.logger.warning('No job name in the message')
            return create_result(messages_pb2.Result.FAIL, error='No job')
        if not message.script_path:
            self.logger.warning('No script path in the message')
            return create_result(messages_pb2.Result.FAIL, error='No script')
        if not os.path.exists(message.script_path):
            self.logger.warning('Script file does not exist!')
            return create_result(messages_pb2.Result.FAIL, error='No such script')
        return None

    def handle_connect_slave(self, message, peername):
        address = (message.address, message.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        if self.client_ssl_context:
            sock = self.client_ssl_context.wrap_socket(sock)
        self.logger.info('{}: Connecting slave: {}'.format(peername, address))
        try:
            sock.connect(address)
        except socket.error as err:
            self.logger.error('Connection error: {}'.format(err))
            return create_result(messages_pb2.Result.FAIL, error='Cannot connect to slave')
        token_request = messages_pb2.SlaveCommand()
        token_request.auth.password = self.auth_handler._password
        sock.send(token_request.SerializeToString())
        data = sock.recv(1024)
        response = messages_pb2.Result()
        response.ParseFromString(data)
        if not response.token:
            self.logger.error('Bad pass!')
            return create_result(messages_pb2.Result.FAIL, error='Bad password')
        self.slaves.append((sock, response.token))
        return create_result(messages_pb2.Result.OK)


def create_post_receive_hook(repo, builderlib_root, port):
    hook_path = os.path.join(repo.working_dir, 'hooks/post-receive')
    template_string = open('../builderlib/post-receive.py', 'r').read()
    post_receive_hook = open(hook_path, 'w')
    post_receive_hook.write(string.Template(template_string)
        .substitute(PATH='\'' + builderlib_root + '\'', PORT=port))
    post_receive_hook.close()
    os.chmod(hook_path, 0o700)


def main(name, certfile=None, keyfile=None, port=None, jobs=None, slaves=None):
    app = Application()
    repo = git.Repo.init(name + '.git', bare=True)
    client_ssl_context = create_client_ssl_context(certfile, keyfile)
    master = Master(AuthenticationManager(read_password()), repo.working_dir, jobs, slaves, client_ssl_context, app.create_server_thread)
    app.create_server(master.create_protocol, port, ssl_context=create_server_ssl_context(certfile, keyfile))
    git_hook_port = app.create_server(master.create_protocol, 0)
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')), git_hook_port)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
