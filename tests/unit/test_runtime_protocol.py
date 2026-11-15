# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the plugin runtime protocol (v1).

The protocol used to be an informal set of dictionaries with a ``type`` key,
spread between the wrapper and the worker. Nothing was versioned, nothing was
validated, and a missing field failed as a ``KeyError`` somewhere deep in the
pipe listener.

These tests pin the normative contract described in
``docs/architecture/plugins/runtime-protocol.md``. They are pure Python: no Qt,
no subprocess, no filesystem.
"""

import pytest

from app.plugin_system.protocol import (
    PROTOCOL_VERSION,
    SUPPORTED_VERSIONS,
    TERMINAL_TYPES,
    Direction,
    InvalidMessage,
    MessageType,
    UnknownMessageType,
    UnsupportedVersion,
    decode,
    direction_of,
    encode,
    negotiate_version,
)


# --- Encoding ---------------------------------------------------------------


def test_encode_wraps_fields_in_a_versioned_envelope():
    raw = encode(MessageType.EXECUTE_TASK, task_id="t1", action_id="copy")

    assert raw["v"] == PROTOCOL_VERSION
    assert raw["type"] == "EXECUTE_TASK"
    assert raw["task_id"] == "t1"
    assert raw["action_id"] == "copy"
    assert "payload" not in raw, "the envelope is flat, not nested"


def test_encode_accepts_a_message_type_name_as_a_string():
    raw = encode("RESULT", task_id="t1", value=42)

    assert raw["type"] == "RESULT"


def test_encode_rejects_an_unknown_message_type():
    with pytest.raises(UnknownMessageType):
        encode("NOT_A_REAL_MESSAGE")


def test_encode_rejects_missing_required_fields():
    with pytest.raises(InvalidMessage) as excinfo:
        encode(MessageType.EXECUTE_TASK, task_id="t1")  # no action_id

    assert "action_id" in str(excinfo.value)


def test_encode_rejects_reserved_envelope_keys():
    with pytest.raises(InvalidMessage):
        encode(MessageType.RESULT, task_id="t1", v=99)

    with pytest.raises(InvalidMessage):
        encode(MessageType.RESULT, task_id="t1", type="ERROR")


def test_encode_rejects_an_unsupported_version():
    with pytest.raises(UnsupportedVersion):
        encode(MessageType.RESULT, version=99, task_id="t1")


# --- Decoding ---------------------------------------------------------------


def test_decode_roundtrips_an_encoded_message():
    raw = encode(MessageType.PROGRESS, task_id="t1", percent=30)

    message = decode(raw)

    assert message.type is MessageType.PROGRESS
    assert message.version == PROTOCOL_VERSION
    assert message["task_id"] == "t1"
    assert message["percent"] == 30


def test_decode_keeps_unknown_fields_for_forward_compatibility():
    raw = encode(MessageType.PROGRESS, task_id="t1", percent=30)
    raw["retry_hint"] = "later"

    message = decode(raw)

    assert message["retry_hint"] == "later"


def test_decode_rejects_a_non_mapping_message():
    for garbage in (b"bytes", "text", ["RESULT"], None, 42):
        with pytest.raises(InvalidMessage):
            decode(garbage)


def test_decode_rejects_a_message_without_type():
    with pytest.raises(InvalidMessage):
        decode({"v": PROTOCOL_VERSION, "task_id": "t1"})


def test_decode_rejects_a_missing_protocol_version():
    with pytest.raises(InvalidMessage):
        decode({"type": "RESULT", "task_id": "t1"})


def test_decode_reports_an_unknown_message_type_separately():
    """Unknown types are logged and ignored, not treated as a broken stream."""
    with pytest.raises(UnknownMessageType) as excinfo:
        decode({"v": PROTOCOL_VERSION, "type": "SOMETHING_NEW"})

    assert excinfo.value.message_type == "SOMETHING_NEW"


def test_decode_rejects_an_unsupported_protocol_version():
    with pytest.raises(UnsupportedVersion) as excinfo:
        decode({"v": 99, "type": "RESULT", "task_id": "t1"})

    assert excinfo.value.received == 99


def test_decode_rejects_missing_required_fields():
    with pytest.raises(InvalidMessage) as excinfo:
        decode({"v": PROTOCOL_VERSION, "type": "PROGRESS", "task_id": "t1"})

    assert "percent" in str(excinfo.value)


def test_decode_accepts_a_process_scoped_error_without_task_id():
    message = decode(
        {
            "v": PROTOCOL_VERSION,
            "type": "ERROR",
            "code": "PLUGIN_UNAVAILABLE",
            "message": "pipe closed",
        }
    )

    assert message.type is MessageType.ERROR
    assert message.get("task_id") is None


def test_decode_accepts_ready_as_the_first_plugin_message():
    message = decode(
        {
            "v": PROTOCOL_VERSION,
            "type": "READY",
            "protocol_version": PROTOCOL_VERSION,
            "plugin_id": "org.quickfile.dummy",
            "plugin_version": "0.1.0",
            "methods": ["get_name"],
        }
    )

    assert message["plugin_id"] == "org.quickfile.dummy"
    assert message["methods"] == ["get_name"]


# --- Semantics --------------------------------------------------------------


def test_terminal_message_types_are_exactly_result_error_and_cancelled():
    assert TERMINAL_TYPES == {
        MessageType.RESULT,
        MessageType.ERROR,
        MessageType.CANCELLED,
    }


@pytest.mark.parametrize(
    "message_type, expected",
    [
        (MessageType.HELLO, Direction.HOST_TO_PLUGIN),
        (MessageType.EXECUTE_TASK, Direction.HOST_TO_PLUGIN),
        (MessageType.CANCEL_TASK, Direction.HOST_TO_PLUGIN),
        (MessageType.PAUSE_TASK, Direction.HOST_TO_PLUGIN),
        (MessageType.RESUME_TASK, Direction.HOST_TO_PLUGIN),
        (MessageType.CALL, Direction.HOST_TO_PLUGIN),
        (MessageType.INPUT_RESPONSE, Direction.HOST_TO_PLUGIN),
        (MessageType.SHUTDOWN, Direction.HOST_TO_PLUGIN),
        (MessageType.READY, Direction.PLUGIN_TO_HOST),
        (MessageType.PROGRESS, Direction.PLUGIN_TO_HOST),
        (MessageType.EVENT, Direction.PLUGIN_TO_HOST),
        (MessageType.RESULT, Direction.PLUGIN_TO_HOST),
        (MessageType.ERROR, Direction.PLUGIN_TO_HOST),
        (MessageType.CANCELLED, Direction.PLUGIN_TO_HOST),
        (MessageType.RETURN, Direction.PLUGIN_TO_HOST),
        (MessageType.INPUT_REQUEST, Direction.PLUGIN_TO_HOST),
        (MessageType.LOG, Direction.PLUGIN_TO_HOST),
        (MessageType.BYE, Direction.PLUGIN_TO_HOST),
    ],
)
def test_every_message_has_an_explicit_direction(message_type, expected):
    assert direction_of(message_type) is expected


def test_direction_of_rejects_unknown_types():
    with pytest.raises(UnknownMessageType):
        direction_of("NOPE")


# --- Version negotiation ----------------------------------------------------


def test_negotiate_version_picks_the_highest_common_version():
    assert negotiate_version(peer_min=1, peer_max=3, supported=(1, 2)) == 2


def test_negotiate_version_accepts_an_exact_match():
    assert negotiate_version(peer_min=2, peer_max=2, supported=(1, 2)) == 2


def test_negotiate_version_fails_when_there_is_no_common_version():
    with pytest.raises(UnsupportedVersion) as excinfo:
        negotiate_version(peer_min=2, peer_max=3, supported=(1,))

    assert excinfo.value.received == 2


def test_negotiate_version_rejects_a_reversed_range():
    with pytest.raises(InvalidMessage):
        negotiate_version(peer_min=3, peer_max=1, supported=SUPPORTED_VERSIONS)


def test_negotiate_version_rejects_non_integer_versions():
    with pytest.raises(InvalidMessage):
        negotiate_version(peer_min="1", peer_max=1, supported=SUPPORTED_VERSIONS)
