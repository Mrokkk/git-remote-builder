#!/bin/env python3

import secrets

class AuthenticationManager:

    tokens = []

    def __init__(self, password):
        self._password = password

    def request_token(self, password):
        if password.strip() == self._password.strip():
            token = secrets.token_hex(16)
            self.tokens.append(token)
            return token
        return None

    def authenticate(self, token):
        if token in self.tokens:
            return True
        return False
