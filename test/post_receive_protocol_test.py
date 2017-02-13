#!/bin/env python3

import pytest
import sys
import os
from unittest.mock import Mock

@pytest.fixture
def post_receive_protocol():
    from builderlib import PostReceiveProtocol
    return PostReceiveProtocol(Mock(), Mock())


def test_making_connection(post_receive_protocol):
    transport_mock = Mock()
    post_receive_protocol.connection_made(transport_mock)
    transport_mock.get_extra_info.assert_called_once_with('peername')


def test_close_connection_when_no_data(post_receive_protocol):
    transport_mock = Mock()
    post_receive_protocol.connection_made(transport_mock)
    post_receive_protocol.data_received('')
    transport_mock.close.assert_called_once()


def test_send_response_when_valid_data(post_receive_protocol):
    transport_mock = Mock()
    post_receive_protocol.connection_made(transport_mock)
    post_receive_protocol.data_received('somedata')
    post_receive_protocol.master.build_request.assert_called_once_with('somedata')
    transport_mock.write.assert_called_once()


def test_can_close_connection(post_receive_protocol):
    transport_mock = Mock()
    post_receive_protocol.connection_made(transport_mock)
    post_receive_protocol.connection_lost(Mock())
    transport_mock.close.assert_called_once()

