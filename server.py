#!/bin/env python3

import logging
import os
import sys
from builderlib.master import Master

def main(argv):
    command = argv[0]
    logfile = os.path.join(os.getcwd(), 'log')
    pidfile = os.path.join(os.getcwd(), '/tmp/server.pid')
    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    master = Master(pidfile=pidfile)
    if command == 'start':
        master.start()
    elif command == 'stop':
        master.stop()
    elif command == 'restart':
        master.restart()


if __name__ == '__main__':
    pwd = os.path.dirname(sys.argv[0])
    main(sys.argv[1:])
