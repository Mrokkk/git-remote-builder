#!/bin/env python3

import sys
import os
import time
from daemons.prefab import run

class Serverd(run.RunDaemon):

    def run(self):
        while True:
            time.sleep(1)

