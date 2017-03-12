#!/bin/env python3

from .slave import *
from builderlib import messages_pb2
from builderlib.protocol import *
from builderlib.authentication import *
from builderlib.messages_handler import *
from builderlib.application import *
from builderlib.utils import *


def main(name, certfile=None, keyfile=None, port=None):
    app = Application(server_ssl_context=create_server_ssl_context(certfile, keyfile))
    slave = Slave(app.create_task, app.create_connection)
    auth_manager = AuthenticationManager(read_password(validate=True))
    messages_handler = MessagesHandler(messages_pb2.SlaveCommand, auth_manager)
    messages_handler.register_handler('build', slave.handle_build_request)
    app.create_server(lambda: Protocol(messages_handler.handle), port)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
