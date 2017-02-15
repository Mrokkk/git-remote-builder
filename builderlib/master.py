#!/bin/env python3

import sys
import os
import ssl
import logging
import getpass
import string
import socket
import git
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from .connection_factory import *
from .application import *
from google.protobuf.text_format import MessageToString


class Master:

    repo_address = None
    slaves = []
    clients = []
    logger = None

    def __init__(self, auth_handler, repo_address):
        self.auth_handler = auth_handler
        self.repo_address = repo_address
        self.messages_handler = MessagesHandler(
            {
                'auth': self.handle_authentication_request,
                'build': self.handle_build_request,
                'connect_slave': self.handle_user_request,
            },
            messages_pb2.MasterCommand)
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
            response.code = messages_pb2.Result.OK
            return response
        else:
            return None


def create_ssl_context(certfile, keyfile):
    if certfile and keyfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile, keyfile=keyfile)
        return ssl_context
    return None


def read_password():
    password = ''
    password = getpass.getpass(prompt='Set password: ')
    if password != getpass.getpass(prompt='Vaildate password: '):
        print('Passwords don\'t match!')
        sys.exit(1)
    return password


def create_post_receive_hook(repo, builderlib_root, port):
    hook_path = os.path.join(repo.working_dir, 'hooks/post-receive')
    template_string = open('../post-receive.py', 'r').read()
    post_receive_hook = open(hook_path, 'w')
    post_receive_hook.write(string.Template(template_string)
        .substitute(PATH='\'' + builderlib_root + '\'', PORT=port))
    post_receive_hook.close()
    os.chmod(hook_path, 0o700)


def main(name, certfile=None, keyfile=None, port=None):
    app = Application()
    repo = git.Repo.init(name + '.git', bare=True)
    master = Master(AuthenticationManager(read_password()), repo.working_dir)
    app.create_server(master.create_protocol, port, ssl_context=create_ssl_context(certfile, keyfile))
    git_hook_port = app.create_server(master.create_protocol, 0)
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')), git_hook_port)
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()
