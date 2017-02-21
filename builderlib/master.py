#!/bin/env python3

import sys
import os
import ssl
import logging
import string
import socket
import git
import subprocess
from . import messages_pb2
from .utils import *
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from google.protobuf.text_format import MessageToString


class Master:

    repo_address = None
    jobs = []
    slaves = []
    clients = []
    logger = None

    def __init__(self, auth_handler, repo_address, jobs, slaves, client_ssl_context):
        self.auth_handler = auth_handler
        self.repo_address = repo_address
        if jobs:
            self.jobs = jobs
        if slaves:
            self.slaves = slaves
        self.messages_handler = MessagesHandler(
            {
                'auth': self.auth_handler.handle_authentication_request,
                'build': self.handle_build_request,
                'connect_slave': self.handle_connect_slave,
                'create_job': self.handle_job_adding
            },
            messages_pb2.MasterCommand)
        self.client_ssl_context = client_ssl_context
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_protocol(self):
        return Protocol(self.messages_handler.handle)

    def handle_build_request(self, message, peername):
        response = messages_pb2.Result()
        self.logger.info('Received new commit {}/{}'.format(message.build.branch, message.build.commit_hash))
        message_to_slave = self.create_slave_build_request(message.build.branch)
        sock = self.slaves[0][0]
        sock.send(message_to_slave.SerializeToString())
        response.code = messages_pb2.Result.OK
        return response

    def create_slave_build_request(self, branch):
        # TODO
        message = messages_pb2.SlaveCommand()
        message.token = self.slaves[0][1]
        message.build.repo_address = os.path.abspath('repo.git')
        message.build.branch = branch
        message.build.log_server_port = self.jobs[0][2]
        message.build.script = open(self.jobs[0][1]).read().encode('ascii')
        return message

    def handle_job_adding(self, message, peername):
        response = messages_pb2.Result()
        if not self.auth_handler.authenticate(message.token):
            return None
        if not message.create_job.name:
            self.logger.warning('No job name in the message')
            response.code = messages_pb2.Result.FAIL
            return response
        if not message.create_job.script_path:
            self.logger.warning('No script path in the message')
            response.code = messages_pb2.Result.FAIL
            return response
        self.logger.info('Adding job: {} with script {}'.format(message.create_job.name,
            message.create_job.script_path))
        try:
            log_server = subprocess.Popen(['../builderlib/log_reader.py'], stdout=subprocess.PIPE, bufsize=1)
            port = int(log_server.stdout.readline().decode('ascii').strip('\n'))
        except:
            self.logger.critical('Cannot start log server')
            response.code = messages_pb2.Result.FAIL
            return response
        self.logger.info('Started log server at port {}'.format(port))
        response.code = messages_pb2.Result.OK
        self.jobs.append((message.create_job.name, os.path.abspath(message.create_job.script_path), port))
        return response

    def handle_connect_slave(self, message, peername):
        response = messages_pb2.Result()
        if not self.auth_handler.authenticate(message.token):
            return None
        address = (message.connect_slave.address, message.connect_slave.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.client_ssl_context:
            sock = self.client_ssl_context.wrap_socket(sock)
        self.logger.info('{}: Connecting slave: {}'.format(peername, address))
        sock.connect(address)
        token_request = messages_pb2.SlaveCommand()
        token_request.auth.password = self.auth_handler._password
        sock.send(token_request.SerializeToString())
        data = sock.recv(1024)
        response.ParseFromString(data)
        if not response.token:
            self.logger.error('Bad pass!')
            response.error = 'Bad password'
            response.code = messages_pb2.Result.FAIL
            return response
        self.slaves.append((sock, response.token))
        response.code = messages_pb2.Result.OK
        return response


def create_post_receive_hook(repo, builderlib_root, port):
    hook_path = os.path.join(repo.working_dir, 'hooks/post-receive')
    template_string = open('../post-receive.py', 'r').read()
    post_receive_hook = open(hook_path, 'w')
    post_receive_hook.write(string.Template(template_string)
        .substitute(PATH='\'' + builderlib_root + '\'', PORT=port))
    post_receive_hook.close()
    os.chmod(hook_path, 0o700)


def main(name, certfile=None, keyfile=None, port=None, jobs=None, slaves=None):
    app = Application()
    repo = git.Repo.init(name + '.git', bare=True)
    client_ssl_context = create_client_ssl_context(certfile, keyfile)
    master = Master(AuthenticationManager(read_password()), repo.working_dir, jobs, slaves, client_ssl_context)
    app.create_server(master.create_protocol, port, ssl_context=create_server_ssl_context(certfile, keyfile))
    git_hook_port = app.create_server(master.create_protocol, 0)
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')), git_hook_port)
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()
