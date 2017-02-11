#!/bin/env python3

import socket
import ssl
import os
import sys
import argparse
from builderlib import messages_pb2
from google.protobuf.text_format import MessageToString

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='use given port', type=int, default=0)
    parser.add_argument('-c', '--cert', help='use given certificate file (SSL)')
    parser.add_argument('-k', '--key', help='use given key file (SSL)')
    args = parser.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', args.port)
    if args.cert and args.key:
        sock = ssl.wrap_socket(sock, certfile=os.path.abspath(args.cert), keyfile=os.path.abspath(args.key))
    try:
        sock.connect(server_address)
    except socket.error as err:
        print('Connection error: {}'.format(err))
        sys.exit(1)
    print('Connected')
    try:
        for line in sys.stdin:
            msg = messages_pb2.Command()
            f = open('examples/build.sh', 'r')
            msg.build.commit_hash = 'b85fe'
            msg.build.script = bytes(f.read(), 'ascii')
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

