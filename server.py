#!/bin/env python3

import logging
import os
import sys
import daemon
import pid
import getopt
import signal
import builderlib.master

def main(argv):
    command = argv[0]
    if command == 'start':
        start_server(argv[1:])
    elif command == 'stop':
        stop_server(argv[1:])


def start_server(argv):
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
    pidfile = pid.PidFile(piddir=os.getcwd())
    with daemon.DaemonContext(working_directory=os.getcwd(),
                              umask=0o077,
                              pidfile=pidfile,
                              stdout=sys.stdout,
                              stderr=sys.stderr):
        builderlib.master.main(certfile=cert, keyfile=key, port=port)


def stop_server(argv):
    pid = open('server.py.pid', 'r').read().strip()
    os.kill(int(pid), signal.SIGTERM)


if __name__ == '__main__':
    pwd = os.path.dirname(sys.argv[0])
    main(sys.argv[1:])

