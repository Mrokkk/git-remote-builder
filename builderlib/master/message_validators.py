#!/bin/env python3


def connect_slave(func):
    def func_wrapper(*args):
        message = args[1]
        if not message.address:
            raise RuntimeError('No address given')
        if not message.port:
            raise RuntimeError('No port given')
        return func(*args)
    return func_wrapper


def create_job(func):
    def func_wrapper(*args):
        if not args[1].name:
            raise RuntimeError('No job name')
        if not args[1].script:
            raise RuntimeError('No script')
        return func(*args)
    return func_wrapper
