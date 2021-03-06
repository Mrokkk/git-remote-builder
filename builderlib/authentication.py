#!/bin/env python3

import secrets
import logging
from . import messages_pb2


class AuthenticationManager:

    tokens = None
    logger = None

    def __init__(self, password):
        self._password = password
        self.tokens = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def __authenticate(self, token):
        if token in self.tokens:
            return True
        self.logger.warning('Bad token {}'.format(token))
        return False

    def request_token(self, password):
        if password.strip() == self._password.strip():
            token = secrets.token_hex(16)
            self.tokens.append(token)
            return token
        return None

    def handle_authentication_request(self, message, peername):
        response = messages_pb2.Result()
        token = self.request_token(message.password)
        if token:
            self.logger.info('Successful authentication')
            response.token = token
        else:
            self.logger.warning('Denied attempt to authenticate with bad password')
            response.error = 'Bad password'
            response.code = messages_pb2.Result.FAIL
        return response

    def authentication_callback(self, message, peername):
        return self.__authenticate(message.token)
