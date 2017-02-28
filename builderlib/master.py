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
    server_factory = None
    logger = None

    class Slave:
        connection = None
        token = None
        free = True

        def __init__(self, address, password, connection_factory):
            self.logger = logging.getLogger("{}.{}".format(self.__class__.__name__, address))
            self.logger.debug('Constructor')
            self.connection = connection_factory(address[0], address[1])
            token_request = messages_pb2.SlaveCommand()
            token_request.auth.password = password
            response = self.connection.send(token_request)
            if not response.token:
                self.logger.error('Bad pass!')
                raise "Bad pass"
            self.token = response.token

        def set_free(self):
            self.logger.info('Finished build')
            self.free = True

        def set_busy(self):
            self.logger.info('Starting build')
            self.free = False

        def send_build_request(self, branch, log_server_port, build_script):
            message = messages_pb2.SlaveCommand()
            message.token = self.token
            message.build.repo_address = os.path.abspath('repo.git')
            message.build.branch = branch
            message.build.log_server_port = log_server_port
            with open(build_script) as f:
                message.build.script = f.read().encode('ascii')
            return self.connection.send(message)

    class Job:
        log_protocol = None
        script_path = None
        port = None

        def __init__(self, name, port, script_path, log_protocol):
            self.name = name
            self.port = port
            self.script_path = script_path
            self.log_protocol = log_protocol
            self.logger = logging.getLogger(self.__class__.__name__ + '.' + name)
            self.logger.debug('Constructor')

    def __init__(self, repo_address, server_factory, connection_factory):
        self.repo_address = repo_address
        self.server_factory = server_factory
        self.connection_factory = connection_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def handle_build_request(self, message, peername):
        self.logger.info('Received new commit {}/{}'.format(message.branch, message.commit_hash))
        response = self.slaves[0].send_build_request(message.branch, self.jobs[0].port, self.jobs[0].script_path)
        log_protocol = self.jobs[0].log_protocol
        log_protocol.set_open_callback(lambda: self.slaves[0].set_busy())
        log_protocol.set_close_callback(lambda: self.slaves[0].set_free())
        return create_result(messages_pb2.Result.OK)

    def handle_job_adding(self, message, peername):
        error = self.validate_job_adding_message(message)
        if error:
            return error
        self.logger.info('Adding job: {} with script {}'.format(message.name,
            message.script_path))
        log_protocol = LogProtocol(message.name)
        port = self.server_factory(lambda: log_protocol)
        if not port:
            return create_result(messages_pb2.Result.FAIL, error='Cannot start log server')
        job = self.Job(message.name, port, os.path.abspath(message.script_path), log_protocol)
        self.jobs.append(job)
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
        self.logger.info('{}: Connecting slave: {}'.format(peername, address))
        try:
            slave = self.Slave((message.address, message.port), message.password, self.connection_factory)
        except socket.error as err:
            self.logger.error('Connection error: {}'.format(err))
            return create_result(messages_pb2.Result.FAIL, error='Cannot connect to slave')
        except:
            self.logger.error('Connection error')
            return create_result(messages_pb2.Result.FAIL, error='Cannot connect to slave')
        self.slaves.append(slave)
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
    app = Application(server_ssl_context=create_server_ssl_context(certfile, keyfile),
                      client_ssl_context=create_client_ssl_context(certfile, keyfile))
    repo = git.Repo.init(name + '.git', bare=True)
    master = Master(repo.working_dir, app.create_server_thread, app.create_connection)
    auth_manager = AuthenticationManager(read_password(validate=True))
    messages_handler = MessagesHandler(messages_pb2.MasterCommand, auth_manager)
    messages_handler.register_handler('build', master.handle_build_request, require_auth=False)
    messages_handler.register_handler('connect_slave', master.handle_connect_slave)
    messages_handler.register_handler('create_job', master.handle_job_adding)
    protocol = Protocol(messages_handler.handle)
    app.create_server(lambda: protocol, port)
    git_hook_port = app.create_server(lambda: protocol, 0, ssl=False)
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')), git_hook_port)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
