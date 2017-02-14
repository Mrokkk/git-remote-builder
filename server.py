#!/bin/env python3

import os
import sys
import argparse
from builderlib import master

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', metavar='NAME')
    parser.add_argument('-p', '--port', help='use given port', type=int)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    parser.add_argument('-c', '--config', help='read config from file')
    parser.add_argument('-m', '--master', help='run master instance', action='store_true')
    args = parser.parse_args()
    cert, key = None, None
    if args.ssl:
        cert = os.path.abspath(args.ssl[0])
        key = os.path.abspath(args.ssl[1])
    workspace = os.path.join(os.getcwd(), 'workspace')
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    os.chdir(workspace)
    if args.master:
        master.main(args.name, certfile=cert, keyfile=key, port=args.port)


if __name__ == '__main__':
    main()

