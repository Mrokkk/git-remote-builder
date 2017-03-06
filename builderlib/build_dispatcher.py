#!/bin/env python3

import threading
import queue
import logging
import time

class BuildDispatcher(threading.Thread):

    queue = None
    logger = None

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = queue.Queue()
        super().__init__(target=self.main_loop, args=(self.queue, ), daemon=True)

    def main_loop(self, queue):
        while True:
            branch, slaves, jobs = queue.get()
            self.logger.info('Got new build for branch {}'.format(branch))
            for job in jobs:
                self.run_job(job, slaves, branch)

    def run_job(self, job, slaves, branch):
        while True:
            for slave in slaves:
                if not slave.free:
                    continue
                try:
                    job.run_in_slave(slave, branch)
                    time.sleep(1)
                    return
                except RuntimeError as exc:
                    return self.error('Error sending build request: {}'.format(exc))
                except Exception as exc:
                    return self.error('Unexpected error: {}'.format(exc))
            time.sleep(0.5)

    def push_build(self, branch, slaves, job):
        self.queue.put((branch, slaves, job))
