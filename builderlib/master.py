#!/bin/env python3

import sys
import os
import ssl
import logging
import asyncio
import getpass
import secrets
import string
from base64 import b64encode
import git
from . import messages_pb2
from . import protocol
from google.protobuf.text_format import MessageToString

class Master:

    msg = 0
    password = None
    repo = None
    logger = None
    slaves = []
    client_token = None

    def __init__(self, password, repo, logger):
        self.password = password
        self.repo = repo
        self.logger = logger.getChild(self.__class__.__name__)
        self.logger.info('Repo at: {}'.format(self.repo.working_dir))
        pass

    def parse_message(self, data):
        self.msg = self.msg + 1
        message = messages_pb2.Command()
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message')
            return None
        response = messages_pb2.Result()
        if not message.token:
            if message.WhichOneof('command') == 'auth':
                return self.handle_authentication_request(message).SerializeToString()
            elif message.build and not message.build.script:
                return self.handle_build_request(message).SerializeToString()
            else:
                self.logger.warning('Message without token. Closing connection')
                return None
        elif message.token == self.client_token:
            return self.handle_user_request(message).SerializeToString()
        else:
            self.logger.warning('Bad token in the message')
        return None

    def handle_authentication_request(self, message):
        response = messages_pb2.Result()
        self.logger.info('Got authentication request')
        if str(message.auth.password).strip() == str(self.password).strip():
            self.client_token = secrets.token_hex(16)
            response.token = self.client_token
            self.logger.info('Accepted request. Sending token')
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
        self.logger.info('{}: {}'.format(self.msg, MessageToString(message, as_one_line=True)))
        response.code = messages_pb2.Result.OK
        return response

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
    repo_path = os.path.join(os.getcwd(), name +  '.git')
    repo = git.Repo.init(repo_path, bare=True)
    master = Master(read_password(), repo, logger)
    loop = asyncio.get_event_loop()
    ssl_context = create_ssl_context(certfile, keyfile)
    main_server = create_server(loop, lambda: protocol.Protocol(master, logger), port, ssl_context=ssl_context)
    git_hook_server = create_server(loop, lambda: protocol.Protocol(master, logger), 0)
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

