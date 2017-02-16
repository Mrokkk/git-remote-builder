#!/bin/env python3

import secrets
import logging
from . import messages_pb2

class AuthenticationManager:

    tokens = []
    logger = None

    def __init__(self, password):
        self._password = password
        self.logger = logging.getLogger(self.__class__.__name__)

    def request_token(self, password):
        if password.strip() == self._password.strip():
            token = secrets.token_hex(16)
            self.tokens.append(token)
            return token
        return None

    def authenticate(self, token):
        if token in self.tokens:
            return True
        self.logger.warning('Bad token {}'.format(token))
        return False

    def handle_authentication_request(self, message, peername):
        response = messages_pb2.Result()
        token = self.request_token(message.auth.password)
        if token:
            self.logger.info('Successful authentication')
            response.token = token
        else:
            self.logger.warning('Denied attempt to authenticate with bad password')
            response.error = 'Bad password'
            response.code = messages_pb2.Result.FAIL
        return response

