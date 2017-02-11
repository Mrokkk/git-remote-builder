#!/bin/env python3

import os
import sys
import argparse
from builderlib import master

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='use given port', type=int)
    parser.add_argument('-c', '--cert', help='use given certificate file (SSL)')
    parser.add_argument('-k', '--key', help='use given key file (SSL)')
    args = parser.parse_args()
    cert, key = None, None
    if args.cert:
        cert = os.path.abspath(args.cert)
    if args.key:
        key = os.path.abspath(args.key)
    master.main(certfile=cert, keyfile=key, port=args.port)


if __name__ == '__main__':
    main()

