#!/bin/env python3

class Build:

    header = 'BUILD'
    commit = None

    def __init__(commit):
        self.commit = commit

    def string(self):
        return 'BUILD ' + self.commit

class Connect:

    header = 'CONNECT'
    hostname = None
    port = None

    def __init__(self, hostname, port):
        self.hostname = hostname
        self.port = port

