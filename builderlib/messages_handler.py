#!/bin/env python3

import logging
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class MessagesHandler:

    msg_num = 0
    callbacks = {}
    message_type = None
    logger = None

    def __init__(self, message_type):
        self.message_type = message_type
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def register_handler(self, message_name, handler, validator=None):
        self.callbacks[message_name] = (handler, validator)

    def handle(self, data, peername):
        message = self.message_type()
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message type')
            return None
        self.msg_num += 1
        try:
            callback = self.callbacks[message.WhichOneof('command')][0]
            validator = self.callbacks[message.WhichOneof('command')][1]
        except:
            self.logger.error('No callback for that message: {}'.format(
                MessageToString(message, as_one_line=True)))
            return None
        if validator:
            if not validator(message, peername):
                return None
        response = callback(eval('message.{}'.format(message.WhichOneof('command'))), peername)
        if not response:
            self.logger.warning('Callback returned None')
            return None
        return response.SerializeToString()
