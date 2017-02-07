#!/bin/env python3

import logging
import os
import sys
import time
from lib import serverd

def main(argv):
    action = sys.argv[1]
    logfile = os.path.join(os.getcwd(), "serverd.log")
    pidfile = os.path.join(os.getcwd(), "serverd.pid")

    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    d = serverd.Serverd(pidfile=pidfile)

    if action == "start":
        d.start()
    elif action == "stop":
        d.stop()
    elif action == "restart":
        d.restart()


if __name__ == '__main__':
    main(sys.argv[1:])
