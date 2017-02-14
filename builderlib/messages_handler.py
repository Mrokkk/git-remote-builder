#!/bin/env python3

import logging
from . import messages_pb2

class MessagesHandler:

    msg_num = 0
    callbacks = None
    message_type = None
    logger = None

    def __init__(self, callbacks, message_type):
        self.callbacks = callbacks
        self.message_type = message_type
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def handle(self, data):
        message = self.message_type()
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message type')
            return None
        self.msg_num += 1
        return self.callbacks[message.WhichOneof('command')](message).SerializeToString()
