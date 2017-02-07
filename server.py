#!/bin/env python3

import logging
import os
import sys
import time
from lib.serverd import ServerDaemon

def main(argv):
    command = argv[0]
    logfile = os.path.join(os.getcwd(), 'log')
    pidfile = os.path.join(os.getcwd(), 'pid')
    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    server = ServerDaemon(pidfile=pidfile)
    if command == 'start':
        server.start()
    elif command == 'stop':
        server.stop()
    elif command == 'restart':
        server.restart()


if __name__ == '__main__':
    main(sys.argv[1:])
