#!/bin/env python3

import logging
from . import messages_pb2
from builderlib.message_helpers import *
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

    def __parse_message(self, data):
        message = self.message_type()
        message.ParseFromString(data)
        return message

    def __handle_auth_message(self, message, peername):
        resp = self.auth_handler.handle_authentication_request(message.auth, peername)
        if not resp:
            return None
        return resp.SerializeToString()

    def __handle_message(self, message, peername):
        try:
            callback = self.callbacks[message.WhichOneof('command')]
        except:
            self.logger.error('No callback for message: {}'.format(
                MessageToString(message, as_one_line=True)))
            return None
        if not self.auth_handler.authentication_callback(message, peername):
            self.logger.warning('Message without token: {}'.format(
                MessageToString(message, as_one_line=True)))
            return None
        try:
            response = callback(eval('message.{}'.format(message.WhichOneof('command'))), peername)
        except RuntimeError as exc:
            self.logger.error('Error in callback: {}'.format(exc))
            return fail_message('Error: {}'.format(exc)).SerializeToString()
        if not response:
            return None
        return response.SerializeToString()

    def register_handler(self, message_name, handler):
        self.callbacks[message_name] = handler

    def handle(self, data, peername):
        try:
            message = self.__parse_message(data)
        except:
            self.logger.warning('Not a message')
            return None
        self.msg_num += 1
        if message.WhichOneof('command') == 'auth':
            return self.__handle_auth_message(message, peername)
        return self.__handle_message(message, peername)
