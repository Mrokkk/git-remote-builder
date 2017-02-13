#!/bin/env python3

import os
import sys
import socket

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', 8090)
    sock.connect(server_address)
    sock.settimeout(10)
    args = input().split()
    commit = args[1]
    print('Adding {} to the build queue...'.format(commit))
    sock.send(bytes(commit, 'ascii'))
    response = sock.recv(32).decode('ascii').strip()
    if response == 'OK':
        print('OK')
    else:
        print('Failed')
        sys.exit(1)
    sock.close()


if __name__ == '__main__':
    main()
