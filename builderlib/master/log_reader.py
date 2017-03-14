#!/bin/env python3


class LogReader:

    def __init__(self, log_name):
        self.log_name = log_name
        self.log_file = open(log_name, 'bw')

    def __del__(self):
        self.log_file.close()

    def reader_callback(self, data):
        self.log_file.write(data)
        self.log_file.flush()
