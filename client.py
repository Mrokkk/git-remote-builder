#!/bin/env python3

import socket
import ssl
import os
import sys
import argparse
import getpass
from builderlib.connection_factory import *
from builderlib import messages_pb2
from google.protobuf.text_format import MessageToString

def create_ssl_context(certfile, keyfile):
    if certfile and keyfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.load_cert_chain(certfile, keyfile)
        return ssl_context
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='use given port', type=int, default=0)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    args = parser.parse_args()
    server_address = ('localhost', args.port)
    ssl_context = create_ssl_context(args.ssl[0], args.ssl[1])
    try:
        sock = ConnectionFactory(ssl_context=ssl_context).create('127.0.0.1', args.port)
    except socket.error as err:
        print('Connection error: {}'.format(err))
        sys.exit(1)
    print('Connected')
    token = ''
    password = getpass.getpass('Type password:')
    token_request = messages_pb2.MasterCommand()
    token_request.auth.password = password
    sock.send(token_request.SerializeToString())
    data = sock.recv(1024)
    response = messages_pb2.Result()
    response.ParseFromString(data)
    if not response.token:
        print('Bad pass!')
        sys.exit(1)
    token = response.token
    print('Got token: {}'.format(token))
    try:
        for line in sys.stdin:
            msg = messages_pb2.MasterCommand()
            msg.connect_slave.address = 'b85fe'
            msg.connect_slave.port = 8090
            msg.token = token
            sock.sendall(msg.SerializeToString())
            data = sock.recv(256)
            if not data:
                print('No response from server')
            response = messages_pb2.Result()
            response.ParseFromString(data)
            print('Server sent: {}'.format(MessageToString(response, as_one_line=True)))
    except KeyboardInterrupt:
        print('Closing connection')
        sock.close()


if __name__ == '__main__':
    main()

