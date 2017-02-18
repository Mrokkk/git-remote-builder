#!/bin/env python3

import sys
import os
import ssl
import logging
import getpass
import string
import socket
import git
import asyncio
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .utils import *
from google.protobuf.text_format import MessageToString
from subprocess import call, Popen


class Slave:

    repo_address = None
    logger = None
    busy = False

    def __init__(self, auth_handler):
        self.auth_handler = auth_handler
        self.messages_handler = MessagesHandler(
            {
                'auth': self.auth_handler.handle_authentication_request,
                'build': self.handle_build_request
            },
            messages_pb2.SlaveCommand)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def create_protocol(self):
        return Protocol(self.messages_handler.handle)

    def handle_build_request(self, message, peername):
        if not self.auth_handler.authenticate(message.token):
            return None
        fail = False
        response = messages_pb2.Result()
        if self.busy:
            response.code = messages_pb2.Result.BUSY
            return response
        self.logger.info('Received new commit {}'.format(message.build.commit_hash))
        if not message.build.repo_address:
            self.logger.warning('No repo address')
            fail = True
        if not message.build.script:
            self.logger.warning('No script')
            fail = True
        if not message.build.branch:
            self.logger.warning('No branch')
            fail = True
        if fail:
            response.code = messages_pb2.Result.FAIL
            return response
        self.repo_name = os.path.basename(message.build.repo_address)
        script_file = open('build.sh', 'w')
        script_file.write(message.build.script.decode('ascii'))
        script_file.close()
        os.chmod('build.sh', 0o700)
        if not os.path.exists(self.repo_name):
            repo = git.Repo.clone_from(message.build.repo_address, self.repo_name)
        asyncio.ensure_future(self.build(self.repo_name, message.build.branch, message.build.commit_hash,
            os.path.abspath('build.sh'), (peername[0], message.build.log_server_port)))
        response.code = messages_pb2.Result.OK
        return response

    async def build(self, repo_name, branch, commit, build_script, address):
        self.busy = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)
        f = sock.makefile('w')
        proc = Popen([build_script], cwd=os.path.join(os.getcwd(), repo_name), stdout=f, universal_newlines=True,
            shell=True)
        f.close()
        proc.wait()
        sock.close()
        self.busy = False
        self.logger.info('Finished build')


def main(name, certfile=None, keyfile=None, port=None):
    app = Application()
    slave = Slave(AuthenticationManager(read_password()))
    app.create_server(slave.create_protocol, port, ssl_context=create_server_ssl_context(certfile, keyfile))
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()
