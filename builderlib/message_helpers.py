#!/bin/env python3

from .messages_pb2 import Result

def create_result(code, error=None, token=None):
    result = Result()
    result.code = code
    if error:
        result.error = error
    if token:
        result.token = token
    return result

def success_message():
    return create_result(Result.OK)

def fail_message(error):
    return create_result(Result.FAIL, error=error)
