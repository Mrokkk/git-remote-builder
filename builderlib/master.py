#!/bin/env python3

import sys
import os
import logging
import string
import socket
import subprocess
from . import messages_pb2
from .message_helpers import create_result
from .utils import *
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .log_protocol import *
from .build_dispatcher import *
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
        free = None
        address = None

        def __init__(self, address, password, connection_factory):
            self.logger = logging.getLogger("{}.{}".format(self.__class__.__name__, address))
            self.logger.debug('Constructor')
            self.address = address
            self.free = True
            self.connection = connection_factory(address[0], address[1])
            token_request = messages_pb2.SlaveCommand()
            token_request.auth.password = password
            response = self.connection.send(token_request)
            if not response.token:
                raise RuntimeError('Bad password')
            self.token = response.token

        def set_free(self):
            self.logger.info('Finished build')
            self.free = True

        def set_busy(self):
            self.logger.info('Starting build')
            self.free = False

        def send_build_request(self, repo_address, branch, log_server_port, script):
            message = messages_pb2.SlaveCommand()
            message.token = self.token
            message.build.repo_address = repo_address
            message.build.branch = branch
            message.build.log_server_port = log_server_port
            message.build.script = script
            self.connection.send(message)

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

    def __init__(self, repo_address, server_factory, connection_factory, task_factory, build_dispatcher):
        self.repo_address = repo_address
        self.server_factory = server_factory
        self.connection_factory = connection_factory
        self.task_factory = task_factory
        self.build_dispatcher = build_dispatcher
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def error(self, error):
        self.logger.error(error)
        return create_result(messages_pb2.Result.FAIL, error=error)

    def handle_build_request(self, message, peername):
        self.logger.info('Received new commit {}/{}'.format(message.branch, message.commit_hash))
        self.build_dispatcher.push_build(message.branch, self.slaves, self.jobs)
        return create_result(messages_pb2.Result.OK)

    def handle_job_adding(self, message, peername):
        try:
            self.validate_job_adding_message(message)
        except RuntimeError as exc:
            return self.error('Error adding job: {}'.format(exc))
        self.logger.info('Adding job: {}'.format(message.name))
        try:
            job = self.Job(message.name, message.script, self.server_factory)
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
            slave = self.Slave((message.address, message.port), message.password, self.connection_factory)
        except Exception as exc:
            return self.error('Error connecting to slave: {}'.format(exc))
        self.slaves.append(slave)
        return create_result(messages_pb2.Result.OK)

    def handle_subscribe_job(self, message, peername):
        job = self.find_job(message.name)
        if not job:
            return self.error('No such job')
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((peername[0], message.port))
        except Exception as exc:
            return self.error('Error connecting to client: {}'.format(exc))
        self.logger.info('{}:{} subscribed for job {}'.format(peername[0], message.port, job.name))
        job.add_reader(self.sock.sendall)
        return create_result(messages_pb2.Result.OK)

    def find_job(self, name):
        for job in self.jobs:
            if job.name == name:
                return job
        return None


def create_post_receive_hook(repo, builderlib_root, port, token):
    hook_path = os.path.join(repo, 'hooks/post-receive')
    template_string = open(os.path.join(builderlib_root, 'builderlib/post-receive.py'), 'r').read()
    post_receive_hook = open(hook_path, 'w')
    post_receive_hook.write(string.Template(template_string)
        .substitute(PATH='\'' + builderlib_root + '\'', PORT=port, TOKEN='\'' + token + '\''))
    post_receive_hook.close()
    os.chmod(hook_path, 0o700)


def create_bare_repo(name):
    repo_path = os.path.join(os.getcwd(), name + '.git')
    if not os.path.exists(repo_path):
        os.mkdir(repo_path)
    proc = subprocess.Popen(['git', 'init', '--bare'], cwd=repo_path)
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
    build_dispatcher = BuildDispatcher(socket.gethostname() + ':' + repo)
    build_dispatcher.start()
    master = Master(repo, app.create_server_thread, app.create_connection, app.create_task, build_dispatcher)
    password = read_password(validate=True)
    auth_manager = AuthenticationManager(password)
    messages_handler = create_master_message_handler(master, auth_manager)
    protocol = Protocol(messages_handler.handle)
    app.create_server(lambda: protocol, port)
    git_hook_token = auth_manager.request_token(password)
    git_hook_port = app.create_server(lambda: protocol, 0, ssl=False)
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')), git_hook_port, git_hook_token)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
