#!/bin/env python3

from . import messages_pb2

class MessagesHandler:

    msg_num = 0

    def __init__(self, callbacks, message_type, logger):
        self.callbacks = callbacks
        self.message_type = message_type
        self.logger = logger.getChild(self.__class__.__name__)

    def handle(self, data):
        message = self.message_type()
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message type')
            return None
        self.msg_num = self.msg_num + 1
        return self.callbacks[message.WhichOneof('command')](message).SerializeToString()
