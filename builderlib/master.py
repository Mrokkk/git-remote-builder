#!/bin/env python3

import sys
import os
import ssl
import logging
import asyncio
import getpass
import string
import git
from . import messages_pb2
from .protocol import *
from .authentication import *
from .messages_handler import *
from google.protobuf.text_format import MessageToString


class Master:

    repo = None
    slaves = []
    clients = []
    logger = None

    def __init__(self, auth_handler, repo, logger):
        self.auth_handler = auth_handler
        self.repo = repo
        self.messages_handler = MessagesHandler(
            {
                'auth': lambda msg: self.handle_authentication_request(msg),
                'build': lambda msg: self.handle_build_request(msg),
                'connect_slave': lambda msg: self.handle_user_request(msg),
            },
            messages_pb2.MasterCommand, logger)
        self.logger = logger.getChild(self.__class__.__name__)

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


def configure_logger(filename):
    date_format = '%Y.%m.%d:%H.%M.%S'
    format_string = '[%(asctime)s:%(levelname).1s:%(name)s]: %(message)s'
    logging.basicConfig(format=format_string,
                        datefmt=date_format,
                        filemode='w',
                        filename=filename,
                        level=logging.DEBUG)
    formatter = logging.Formatter(format_string, datefmt=date_format)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.addHandler(console)
    return logger


def create_server(loop, proto, port, ssl_context=None):
    coro = loop.create_server(proto, host='127.0.0.1', port=port, ssl=ssl_context)
    return loop.run_until_complete(coro)


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
    os.umask(0o077)
    logger = configure_logger('log')
    auth_handler = AuthenticationManager(read_password())
    repo_path = os.path.join(os.getcwd(), name +  '.git')
    repo = git.Repo.init(repo_path, bare=True)
    master = Master(auth_handler, repo, logger)
    loop = asyncio.get_event_loop()
    ssl_context = create_ssl_context(certfile, keyfile)
    main_server = create_server(loop, lambda: Protocol(lambda data: master.messages_handler.handle(data), logger),
        port, ssl_context=ssl_context)
    git_hook_server = create_server(loop, lambda: Protocol(lambda data: master.messages_handler.handle(data), logger), 0)
    logger.info('Main server running on {}'.format(main_server.sockets[0].getsockname()))
    logger.info('Post-receive server running on {}'.format(git_hook_server.sockets[0].getsockname()))
    create_post_receive_hook(repo, os.path.abspath(os.path.join(os.getcwd(), '..')),
        git_hook_server.sockets[0].getsockname()[1])
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('\nInterrupted')
        pass
    finally:
        git_hook_server.close()
        main_server.close()
        loop.close()

