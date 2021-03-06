#!/bin/env python3

import os
import sys
import pathlib
import logging
from os import path, chdir, umask
from argparse import ArgumentParser


def configure_logger(filename):
    date_format = '%Y.%m.%d:%H.%M.%S'
    format_string = '[%(asctime)s:%(levelname).1s:%(name)s]: %(message)s'
    logging.basicConfig(format=format_string,
                        datefmt=date_format,
                        filemode='w',
                        filename=filename,
                        level=logging.DEBUG)
    formatter = logging.Formatter(format_string, datefmt=date_format)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.addHandler(console)
    return logger

def get_args():
    parser = ArgumentParser()
    parser.add_argument('name', metavar='NAME')
    parser.add_argument('-p', '--port', help='use given port', type=int)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    parser.add_argument('-c', '--config', help='read config from file')
    parser.add_argument('-m', '--master', help='run master instance', action='store_true')
    return parser.parse_args()

def main():
    args = get_args()
    cert, key = None, None
    if args.ssl:
        cert = os.path.abspath(args.ssl[0])
        key = os.path.abspath(args.ssl[1])
    workspace = pathlib.Path.cwd() / 'workspace'
    workspace.mkdir(exist_ok=True)
    chdir(str(workspace))
    umask(0o077)
    logger = configure_logger('log')
    if args.master:
        from builderlib.master import main as master
        master.main(args.name, certfile=cert, keyfile=key, port=args.port)
    else:
        from builderlib.slave import main as slave
        slave.main(args.name, certfile=cert, keyfile=key, port=args.port)


if __name__ == '__main__':
    main()

