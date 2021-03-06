#!/bin/env python3

import os
import socket
import pathlib
import logging
from subprocess import call, Popen, DEVNULL, PIPE
from google.protobuf.text_format import MessageToString
from builderlib.message_helpers import success_message, fail_message, busy_message


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
    busy = None

    def __init__(self, task_factory, connection_factory):
        self.task_factory = task_factory
        self.connection_factory = connection_factory
        self.logger = logging.getLogger(self.__class__.__name__)
        self.busy = False
        self.logger.debug('Constructor')

    def handle_build_request(self, message, peername):
        if self.busy:
            return busy_message()
        try:
            self.validate_build_message(message)
        except RuntimeError as exc:
            return self.error('Error validating message: {}'.format(exc))
        self.logger.info('Received new commit {}'.format(message.commit_hash))
        self.repo_name = pathlib.Path(message.repo_address).stem
        script_path = pathlib.Path('build.sh')
        with script_path.open(mode='w') as script_file:
            script_file.write(message.script.decode('ascii'))
        script_path.chmod(0o700)
        self.busy = True
        self.task_factory(lambda: self.build(self.repo_name, message.repo_address, message.branch,
            message.commit_hash, str(script_path.resolve()), (peername[0], message.log_server_port)))
        return success_message()

    def validate_build_message(self, message):
        if not message.repo_address:
            raise RuntimeError('No repo address')
        if not message.script:
            raise RuntimeError('No script')
        if not message.branch:
            raise RuntimeError('No branch')
        addr = message.repo_address.split(':')
        if addr[0] == socket.gethostname():
            message.repo_address = addr[1]

    def error(self, error):
        self.logger.error(error)
        return fail_message(error)

    def build(self, repo_name, repo_address, branch, commit, build_script, address):
        try:
            connection = self.connection_factory(address[0], address[1])
        except Exception as exc:
            return self.error('Cannot connect to log server: {}'.format(exc))
        self.logger.info('Writing build of {} to {}'.format(branch, address))
        if not os.path.exists(repo_name):
            clone_repo(repo_address, branch)
        checkout_branch(repo_name, branch, self.logger)
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


