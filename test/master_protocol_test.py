#!/bin/env python3

import pytest
import sys
import os
from unittest.mock import Mock

@pytest.fixture
def master_protocol():
    from builderlib import MasterProtocol
    return MasterProtocol(Mock(), Mock())


def test_making_connection(master_protocol):
    transport_mock = Mock()
    master_protocol.connection_made(transport_mock)
    transport_mock.get_extra_info.assert_called_once_with('peername')


def test_close_connection_when_no_data(master_protocol):
    transport_mock = Mock()
    master_protocol.connection_made(transport_mock)
    master_protocol.data_received('')
    transport_mock.close.assert_called_once()
    pass


def test_close_connection_when_data_not_valid(master_protocol):
    transport_mock = Mock()
    master_protocol.master.parse_message.return_value = None
    master_protocol.connection_made(transport_mock)
    master_protocol.data_received('somedata')
    transport_mock.close.assert_called_once()
    pass


def test_send_response_when_valid_data(master_protocol):
    transport_mock = Mock()
    master_protocol.connection_made(transport_mock)
    master_protocol.data_received('somedata')
    master_protocol.master.parse_message.assert_called_once_with('somedata')
    transport_mock.write.assert_called_once()
    pass


def test_can_close_connection(master_protocol):
    transport_mock = Mock()
    master_protocol.connection_made(transport_mock)
    master_protocol.connection_lost(Mock())
    transport_mock.close.assert_called_once()

