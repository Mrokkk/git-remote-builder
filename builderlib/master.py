#!/bin/env python3

import sys
import os
import ssl
import logging
import string
import socket
import git
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
        self.jobs = jobs
        self.slaves = slaves
        self.messages_handler = MessagesHandler(
            {
                'auth': self.handle_authentication_request,
                'build': self.handle_build_request,
                'connect_slave': self.handle_user_request,
            },
            messages_pb2.MasterCommand)
        self.client_ssl_context = client_ssl_context
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_protocol(self):
        return Protocol(lambda data: self.messages_handler.handle(data))

    def handle_authentication_request(self, message):
        response = messages_pb2.Result()
        self.logger.info('Got authentication request')
        token = self.auth_handler.request_token(message.auth.password)
        if token:
            response.token = token
        else:
            self.logger.warning('Denied attempt to authenticate with bad password')
            response.code = messages_pb2.Result.FAIL
        return response

    def handle_build_request(self, message):
        response = messages_pb2.Result()
        self.logger.info('Received new commit {}'.format(message.build.commit_hash))
        response.code = messages_pb2.Result.OK
        return response

    def handle_user_request(self, message):
        response = messages_pb2.Result()
        if self.auth_handler.authenticate(message.token):
            self.logger.info('{}'.format(MessageToString(message, as_one_line=True)))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.client_ssl_context:
                sock = self.client_ssl_context.wrap_socket(sock)
            sock.connect(('localhost', 8090))
            message_to_slave = messages_pb2.SlaveCommand()
            message_to_slave.build.script = b'test'
            sock.send(message_to_slave.SerializeToString())
            sock.close()
            response.code = messages_pb2.Result.OK
            return response
        else:
            return None


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
