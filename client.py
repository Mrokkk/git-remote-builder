#!/bin/env python3

import socket
import ssl
import os
import sys
import getopt
from base64 import b64encode

def main(argv):
    port = None
    cert = None
    key = None
    try:
        opts, args = getopt.getopt(argv, "hp:c:k:", ["help", "port=", "cert=", "key="])
    except getopt.GetoptError:
        sys.exit(1)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            sys.exit(0)
        elif opt in ('-p', '--port'):
            port = int(arg)
        elif opt in ('-c', '--cert'):
            cert = os.path.abspath(arg)
        elif opt in ('-k', '--key'):
            key = os.path.abspath(arg)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', int(port))
    if cert and key:
        sock = ssl.wrap_socket(sock, certfile=cert, keyfile=key)
    try:
        sock.connect(server_address)
        print('Connected')
    except:
        print('Cannot connect to {}'.format(server_address))
        sys.exit(1)
    try:
        for line in sys.stdin:
            sock.sendall(b64encode(bytes(line, 'ascii')))
    except KeyboardInterrupt:
        print('Closing connection')
        sock.close()


if __name__ == '__main__':
    pwd = os.path.dirname(sys.argv[0])
    main(sys.argv[1:])

