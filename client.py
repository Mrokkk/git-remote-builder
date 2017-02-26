#!/bin/env python3

import socket
import ssl
import os
import sys
import argparse
import getpass
import readline
from builderlib.connection_factory import *
from builderlib.utils import *
from builderlib import messages_pb2
from google.protobuf.text_format import MessageToString


class Completer:

    def __init__(self, options):
        self.options = sorted(options)
        self.matches = None
        return

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='use given port', type=int, default=0)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    args = parser.parse_args()
    ssl_context = create_client_ssl_context(args.ssl[0], args.ssl[1])
    try:
        sock = ConnectionFactory(ssl_context=ssl_context).create('127.0.0.1', args.port)
    except socket.error as err:
        print('Connection error: {}'.format(err))
        sys.exit(1)
    token = authenticate(sock)
    readline.parse_and_bind('tab: complete')
    readline.set_completer(Completer(['connect', 'create']).complete)
    try:
        while True:
            read_and_send(sock, token)
    except KeyboardInterrupt:
        print('Closing connection')
        sock.close()


def authenticate(sock):
    token = ''
    token_request = messages_pb2.MasterCommand()
    token_request.auth.password = read_password()
    sock.send(token_request.SerializeToString())
    data = sock.recv(1024)
    response = messages_pb2.Result()
    response.ParseFromString(data)
    if not response.token:
        print('Bad pass!')
        sys.exit(1)
    token = response.token
    print('Got token: {}'.format(token))
    return token

def read_and_send(sock, token):
    line = input('> ').strip('\r\n')
    msg = messages_pb2.MasterCommand()
    msg.token = token
    args = line.split()
    command = args[0]
    args = args[1:]
    if command == 'connect':
        msg.connect_slave.address = args[0]
        msg.connect_slave.port = int(args[1])
        msg.connect_slave.password = read_password()
    elif command == 'create':
        msg.create_job.name = args[0]
        msg.create_job.script_path = args[1]
    else:
        return
    sock.sendall(msg.SerializeToString())
    data = sock.recv(256)
    if not data:
        print('No response from server')
    response = messages_pb2.Result()
    response.ParseFromString(data)
    print('Server sent: {}'.format(MessageToString(response, as_one_line=True)))


if __name__ == '__main__':
    main()

