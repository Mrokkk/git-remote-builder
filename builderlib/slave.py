#!/bin/env python3

import sys
import os
import logging
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from .application import *
from .utils import *
from .message_helpers import *
from google.protobuf.text_format import MessageToString
from subprocess import call, Popen, DEVNULL, PIPE


def clone_repo(repo_address, branch=None):
    proc = Popen(['git', 'clone', repo_address])
    proc.wait()


def checkout_branch(path, branch, logger):
    proc = Popen(['git', 'fetch', 'origin', branch], cwd=path, stdout=DEVNULL, stderr=DEVNULL)
    errors = proc.communicate()
    proc = Popen(['git', 'checkout', 'origin/' + branch], cwd=path, stdout=DEVNULL, stderr=DEVNULL)
    errors = proc.communicate()
    proc = Popen(['git', 'submodule', 'update', '--init', '--recursive'], cwd=path, stdout=DEVNULL, stderr=DEVNULL)
    errors = proc.communicate()


class Slave:

    repo_address = None
    logger = None
    busy = False

    def __init__(self, task_factory, connection_factory):
        self.task_factory = task_factory
        self.connection_factory = connection_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def handle_build_request(self, message, peername):
        if self.busy:
            return create_result(messages_pb2.Result.BUSY)
        try:
            self.validate_build_message(message)
        except RuntimeError as exc:
            return self.error('Error validating message: {}'.format(exc))
        addr = message.repo_address.split(':')
        if addr[0] == socket.gethostname():
            message.repo_address = addr[1]
        self.logger.info('Received new commit {}'.format(message.commit_hash))
        self.repo_name = os.path.splitext(os.path.basename(message.repo_address))[0]
        with open('build.sh', 'w') as script_file:
            script_file.write(message.script.decode('ascii'))
        os.chmod('build.sh', 0o700)
        self.busy = True
        self.task_factory(lambda: self.build(self.repo_name, message.repo_address, message.branch,
            message.commit_hash, os.path.abspath('build.sh'), (peername[0], message.log_server_port)))
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

    def build(self, repo_name, repo_address, branch, commit, build_script, address):
        if not os.path.exists(repo_name):
            clone_repo(repo_address, branch)
        checkout_branch(repo_name, branch, self.logger)
        self.logger.info('Writing build of {} to {}'.format(branch, address))
        try:
            connection = self.connection_factory(address[0], address[1])
        except Exception as exc:
            return self.error('Cannot connect to log server: {}'.format(exc))
        f = connection.file('w')
        f.write('Starting build for commit "{}" and branch "{}"\n'.format(commit, branch))
        f.flush()
        proc = Popen([build_script], cwd=os.path.join(os.getcwd(), repo_name), stdout=f, stderr=f,
            universal_newlines=True, shell=True, bufsize=1)
        proc.wait()
        if proc.returncode:
            f.write('\033[1;31m[BUILD FAILED]\033[0m\n')
        else:
            f.write('\033[1;32m[BUILD PASSED]\033[0m\n')
        self.logger.info('Finished build')
        f.close()
        self.busy = False


def main(name, certfile=None, keyfile=None, port=None):
    app = Application(server_ssl_context=create_server_ssl_context(certfile, keyfile))
    slave = Slave(app.create_task, app.create_connection)
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
