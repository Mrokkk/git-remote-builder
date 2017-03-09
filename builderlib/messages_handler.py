#!/bin/env python3

import logging
from . import messages_pb2
from google.protobuf.text_format import MessageToString

class MessagesHandler:

    msg_num = None
    callbacks = None
    message_type = None
    logger = None
    auth_handler = None

    def __init__(self, message_type, auth_handler):
        self.message_type = message_type
        self.auth_handler = auth_handler
        self.callbacks = {}
        self.msg_num = 0
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Constructor')

    def register_handler(self, message_name, handler):
        self.callbacks[message_name] = handler

    def handle(self, data, peername):
        message = self.message_type()
        try:
            message.ParseFromString(data)
        except:
            self.logger.warning('Bad message type')
            return None
        self.msg_num += 1
        if message.WhichOneof('command') == 'auth':
            resp = self.auth_handler.handle_authentication_request(message.auth, peername)
            if not resp:
                return None
            return resp.SerializeToString()
        try:
            callback = self.callbacks[message.WhichOneof('command')]
        except:
            self.logger.error('No callback for message: {}'.format(
                MessageToString(message, as_one_line=True)))
            return None
        if not self.auth_handler.authentication_callback(message, peername):
            return None
        response = callback(eval('message.{}'.format(message.WhichOneof('command'))), peername)
        if not response:
            self.logger.warning('Callback returned None')
            return None
        return response.SerializeToString()
