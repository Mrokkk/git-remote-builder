#!/bin/env python3

import sys
import os
import logging
import string
import socket
import git
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .utils import *
from .message_helpers import *
from google.protobuf.text_format import MessageToString
from subprocess import call, Popen


class Slave:

    repo_address = None
    logger = None
    busy = False

    def __init__(self, task_factory):
        self.task_factory = task_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def handle_build_request(self, message, peername):
        if self.busy:
            return create_result(messages_pb2.Result.BUSY)
        try:
            self.validate_build_message(message)
        except RuntimeError as exc:
            return self.error('Error validating message: {}'.format(exc))
        self.logger.info('Received new commit {}'.format(message.commit_hash))
        self.repo_name = os.path.basename(message.repo_address)
        with open('build.sh', 'w') as script_file:
            script_file.write(message.script.decode('ascii'))
        os.chmod('build.sh', 0o700)
        if not os.path.exists(self.repo_name):
            repo = git.Repo.clone_from(message.repo_address, self.repo_name)
        self.task_factory(lambda: self.build(self.repo_name, message.branch, message.commit_hash,
            os.path.abspath('build.sh'), (peername[0], message.log_server_port)))
        return create_result(messages_pb2.Result.OK)

    def validate_build_message(self, message):
        if not message.repo_address:
            raise RuntimeError('No repo address')
        if not message.script:
            raise RuntimeError('No script')
        if not message.branch:
            raise RuntimeError('No branch')

    def error(self, error):
        self.logger.error(error)
        return create_result(messages_pb2.Result.FAIL, error=error)

    async def build(self, repo_name, branch, commit, build_script, address):
        self.logger.info('Writing to {}'.format(address))
        self.busy = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)
        f = sock.makefile('w')
        proc = Popen([build_script], cwd=os.path.join(os.getcwd(), repo_name), stdout=f, stderr=f, universal_newlines=True,
            shell=True)
        proc.wait()
        self.logger.info('Finished build')
        f.close()
        sock.close()
        self.busy = False


def main(name, certfile=None, keyfile=None, port=None):
    app = Application(server_ssl_context=create_server_ssl_context(certfile, keyfile))
    slave = Slave(app.create_task)
    auth_manager = AuthenticationManager(read_password(validate=True))
    messages_handler = MessagesHandler(messages_pb2.SlaveCommand, auth_manager)
    messages_handler.register_handler('build', slave.handle_build_request)
    app.create_server(lambda: Protocol(messages_handler.handle), port)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
