#/bin/env python3

import sys
import os
import ssl
import getpass

def create_client_ssl_context(certfile, keyfile):
    if certfile and keyfile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.load_cert_chain(certfile, keyfile=keyfile)
        return ssl_context
    return None


def create_server_ssl_context(certfile, keyfile):
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
