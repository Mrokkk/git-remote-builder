#!/bin/env python3

import os
import sys
import socket

sys.path.insert(1, os.path.abspath(os.path.join(os.getcwd(), '../')))

from builderlib import messages_pb2

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', 8090)
    sock.connect(server_address)
    sock.settimeout(10)
    args = input().split()
    commit = args[1]
    print('Adding {} to the build queue...'.format(commit))
    msg = messages_pb2.Command()
    msg.build.commit_hash = commit
    sock.send(msg.SerializeToString())
    response = messages_pb2.Result()
    data = sock.recv(256)
    response.ParseFromString(data)
    if response.code == messages_pb2.Result.OK:
        print('OK')
    else:
        print('Failed')
        sys.exit(1)
    sock.close()


if __name__ == '__main__':
    main()
