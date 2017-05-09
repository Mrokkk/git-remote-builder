#!/bin/env python3

import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--host', help='hostname', default='127.0.0.1')
    parser.add_argument('-p', '--port', help='use given port', type=int, default=0)
    parser.add_argument('-s', '--ssl', help='use SLL with given certificate and key', nargs=2, metavar=('CERT', 'KEY'))
    return parser.parse_args()

def main():
    args = parse_args()
    cert, key = None, None
    if args.ssl:
        cert = args.ssl[0]
        key = args.ssl[1]
    from builderlib.client import main as client
    client.main(args.host, args.port, cert, key)

if __name__ == '__main__':
    main()
