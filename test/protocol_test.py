#!/bin/env python3

import pytest
import sys
import os
from unittest.mock import Mock

@pytest.fixture
def protocol():
    from builderlib.protocol import Protocol
    return Protocol(Mock())


def test_making_connection(protocol):
    transport_mock = Mock()
    protocol.connection_made(transport_mock)
    transport_mock.get_extra_info.assert_called_once_with('peername')


def test_close_connection_when_no_data(protocol):
    transport_mock = Mock()
    protocol.connection_made(transport_mock)
    protocol.data_received('')
    transport_mock.close.assert_called_once()


def test_close_connection_when_data_not_valid(protocol):
    transport_mock = Mock()
    protocol.message_handler.return_value = None
    protocol.connection_made(transport_mock)
    protocol.data_received('somedata')
    transport_mock.close.assert_called_once()


def test_send_response_when_valid_data(protocol):
    transport_mock = Mock()
    protocol.connection_made(transport_mock)
    protocol.data_received('somedata')
    protocol.message_handler.assert_called_once_with('somedata')
    transport_mock.write.assert_called_once()


def test_can_close_connection(protocol):
    transport_mock = Mock()
    protocol.connection_made(transport_mock)
    protocol.connection_lost(Mock())
    transport_mock.close.assert_called_once()

