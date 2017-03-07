#!/bin/env python3

import socket
import ssl
import os
import sys
import argparse
import getpass
import readline
import asyncio
from builderlib.utils import *
from builderlib import messages_pb2
from builderlib.application import Application
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
    parser.add_argument('-a', '--host', help='hostname', default='127.0.0.1')
    parser.add_argument('-p', '--port', help='use given port', type=int, default=0)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    args = parser.parse_args()
    ssl_context = None
    if args.ssl:
        ssl_context = create_client_ssl_context(args.ssl[0], args.ssl[1])
    app = Application(client_ssl_context=ssl_context)
    try:
        connection = app.create_connection(args.host, args.port)
    except socket.error as err:
        print('Connection error: {}'.format(err))
        sys.exit(1)
    token = authenticate(connection)
    readline.parse_and_bind('tab: complete')
    readline.set_completer(Completer(['connect', 'create']).complete)
    try:
        while True:
            read_and_send(connection, token)
    except KeyboardInterrupt:
        print('Closing connection')

def authenticate(connection):
    token = ''
    token_request = messages_pb2.MasterCommand()
    token_request.auth.password = read_password()
    response = connection.send(token_request)
    if not response.token:
        print('Bad pass!')
        sys.exit(1)
    token = response.token
    print('Got token: {}'.format(token))
    return token

class ClientLogProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        print('Got connection!')
        self.peername = transport.get_extra_info('peername')
        self.transport = transport

    def connection_lost(self, exc):
        print('Lost connection!')
        self.transport.close()

    def data_received(self, data):
        print(data.decode('utf-8'), end='', flush=True)

def create_server():
    loop = asyncio.get_event_loop()
    coro = loop.create_server(ClientLogProtocol, host='0.0.0.0')
    server = loop.run_until_complete(coro)
    print('Created server at {}'.format(server.sockets[0].getsockname()))
    return loop, server.sockets[0].getsockname()[1]

def read_and_send(connection, token):
    line = input('> ').strip('\r\n')
    msg = messages_pb2.MasterCommand()
    msg.token = token
    args = line.split()
    command = args[0]
    loop = None
    args = args[1:]
    if command == 'connect':
        msg.connect_slave.address = args[0]
        msg.connect_slave.port = int(args[1])
        msg.connect_slave.password = read_password()
    elif command == 'create':
        msg.create_job.name = args[0]
        try:
            with open(args[1], 'r') as f:
                msg.create_job.script = f.read().encode('utf-8')
        except OSError as exc:
            print('Error: {}'.format(exc))
            return
    elif command == 'subscr':
        msg.subscribe_job.name = args[0]
        loop, msg.subscribe_job.port = create_server()
    else:
        return
    try:
        response = connection.send(msg)
    except RuntimeError as exc:
        print('RuntimeError: {}'.format(exc))
        return
    except Exception as exc:
        print('Unexpected error: {}'.format(exc))
        return
    if response.code == messages_pb2.Result.FAIL:
        print('Server returned: {}'.format(response.error))
        return
    if loop:
        loop.run_forever()

if __name__ == '__main__':
    main()
