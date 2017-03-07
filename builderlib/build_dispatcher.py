#!/bin/env python3

import threading
import queue
import logging
import time

class BuildDispatcher(threading.Thread):

    queue = None
    logger = None

    def __init__(self, repo_address):
        self.repo_address = repo_address
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = queue.Queue()
        super().__init__(target=self.main_loop, args=(self.queue, ), daemon=True)

    def main_loop(self, queue):
        while True:
            branch, slaves, jobs = queue.get()
            for job in jobs:
                self.run_job(job, slaves, branch)

    def run_job(self, job, slaves, branch):
        while True:
            for slave in slaves:
                if not slave.free:
                    continue
                try:
                    self.run_in_slave(job, slave, branch)
                    time.sleep(5)
                    return
                except RuntimeError as exc:
                    self.logger.error('Error sending build request: {}'.format(exc))
                    return
                except Exception as exc:
                    self.logger.critical('Unexpected error: {}'.format(exc))
                    return
            time.sleep(0.5)

    def run_in_slave(self, job, slave, branch):
        self.logger.info('Starting job {} for branch "{}"'.format(job.name, branch))
        job.log_protocol.set_open_callback(lambda: slave.set_busy())
        job.log_protocol.set_close_callback(lambda: slave.set_free())
        slave.send_build_request(self.repo_address, branch, job.port, job.script)
        self.logger.info('Sent build command to {}'.format(slave.address))

    def push_build(self, branch, slaves, job):
        self.queue.put((branch, slaves, job))
