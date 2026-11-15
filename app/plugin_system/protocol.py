# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Versioned message protocol between the host and a plugin process.

This module is deliberately free of Qt, multiprocessing and filesystem access:
it only turns dictionaries into validated messages and back. The runtime owns
the transport (see ``docs/architecture/plugins/runtime-protocol.md``).

The protocol is intentionally small. A plugin process exists to run tasks, to
report progress and to answer a few cheap queries; everything else belongs to
the host.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum
from typing import Any, Iterable, Mapping

PROTOCOL_VERSION = 1
SUPPORTED_VERSIONS = (1,)

# Envelope keys that a message body must never override.
RESERVED_FIELDS = frozenset({"v", "type"})


class MessageType(StrEnum):
    """Every message type understood by protocol v1."""

    # Host -> plugin
    HELLO = "HELLO"
    EXECUTE_TASK = "EXECUTE_TASK"
    CANCEL_TASK = "CANCEL_TASK"
    PAUSE_TASK = "PAUSE_TASK"
    RESUME_TASK = "RESUME_TASK"
    CALL = "CALL"
    INPUT_RESPONSE = "INPUT_RESPONSE"
    SHUTDOWN = "SHUTDOWN"

    # Plugin -> host
    READY = "READY"
    PROGRESS = "PROGRESS"
    EVENT = "EVENT"
    RESULT = "RESULT"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    RETURN = "RETURN"
    INPUT_REQUEST = "INPUT_REQUEST"
    LOG = "LOG"
    BYE = "BYE"


class Direction(StrEnum):
    HOST_TO_PLUGIN = "host->plugin"
    PLUGIN_TO_HOST = "plugin->host"


class ErrorCode(StrEnum):
    """Stable error codes carried by ``ERROR`` messages.

    The UI may map these; a host that does not recognise a code must treat it
    as ``INTERNAL``.
    """

    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    PLUGIN_UNAVAILABLE = "PLUGIN_UNAVAILABLE"
    CANCEL_TIMEOUT = "CANCEL_TIMEOUT"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


@dataclasses.dataclass(frozen=True)
class MessageSpec:
    direction: Direction
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


MESSAGE_SPECS: dict[MessageType, MessageSpec] = {
    # Host -> plugin
    MessageType.HELLO: MessageSpec(
        Direction.HOST_TO_PLUGIN,
        required=("protocol_min", "protocol_max", "plugin_id"),
        optional=("host_version",),
    ),
    MessageType.EXECUTE_TASK: MessageSpec(
        Direction.HOST_TO_PLUGIN,
        required=("task_id", "action_id"),
        optional=("kwargs",),
    ),
    MessageType.CANCEL_TASK: MessageSpec(Direction.HOST_TO_PLUGIN, required=("task_id",)),
    MessageType.PAUSE_TASK: MessageSpec(Direction.HOST_TO_PLUGIN, required=("task_id",)),
    MessageType.RESUME_TASK: MessageSpec(Direction.HOST_TO_PLUGIN, required=("task_id",)),
    MessageType.CALL: MessageSpec(
        Direction.HOST_TO_PLUGIN,
        required=("call_id", "method"),
        optional=("args", "kwargs"),
    ),
    MessageType.INPUT_RESPONSE: MessageSpec(
        Direction.HOST_TO_PLUGIN, required=("request_id", "value")
    ),
    MessageType.SHUTDOWN: MessageSpec(Direction.HOST_TO_PLUGIN, optional=("reason",)),
    # Plugin -> host
    MessageType.READY: MessageSpec(
        Direction.PLUGIN_TO_HOST,
        required=("protocol_version", "plugin_id", "plugin_version", "methods"),
    ),
    MessageType.PROGRESS: MessageSpec(
        Direction.PLUGIN_TO_HOST, required=("task_id", "percent")
    ),
    MessageType.EVENT: MessageSpec(
        Direction.PLUGIN_TO_HOST, required=("task_id", "name"), optional=("payload",)
    ),
    MessageType.RESULT: MessageSpec(
        Direction.PLUGIN_TO_HOST, required=("task_id",), optional=("value",)
    ),
    MessageType.ERROR: MessageSpec(
        Direction.PLUGIN_TO_HOST,
        required=("code", "message"),
        optional=("task_id", "traceback"),
    ),
    MessageType.CANCELLED: MessageSpec(Direction.PLUGIN_TO_HOST, required=("task_id",)),
    MessageType.RETURN: MessageSpec(
        Direction.PLUGIN_TO_HOST,
        required=("call_id", "ok"),
        optional=("value", "error", "traceback"),
    ),
    MessageType.INPUT_REQUEST: MessageSpec(
        Direction.PLUGIN_TO_HOST,
        required=("request_id", "name"),
        optional=("task_id", "payload"),
    ),
    MessageType.LOG: MessageSpec(
        Direction.PLUGIN_TO_HOST, required=("level", "message"), optional=("task_id",)
    ),
    MessageType.BYE: MessageSpec(Direction.PLUGIN_TO_HOST, optional=("reason",)),
}

#: A task is finished after exactly one of these messages.
TERMINAL_TYPES = frozenset(
    {MessageType.RESULT, MessageType.ERROR, MessageType.CANCELLED}
)


class ProtocolError(Exception):
    """Base class for every protocol violation."""


class UnknownMessageType(ProtocolError):
    """The message type is not part of this protocol version.

    The runtime logs it and keeps listening: a newer plugin may send a message
    that an older host does not understand, which is not a broken stream.
    """

    def __init__(self, message_type: str):
        self.message_type = message_type
        super().__init__(f"Unknown message type: {message_type!r}")


class UnsupportedVersion(ProtocolError):
    """No common protocol version between the two peers."""

    def __init__(self, received: int, supported: Iterable[int] = SUPPORTED_VERSIONS):
        self.received = received
        self.supported = tuple(supported)
        super().__init__(
            f"Unsupported protocol version {received}, supported: {list(self.supported)}"
        )


class InvalidMessage(ProtocolError):
    """The message does not match the envelope or its type's schema."""


def _coerce_type(message_type: str | MessageType) -> MessageType:
    try:
        return MessageType(message_type)
    except ValueError:
        raise UnknownMessageType(str(message_type)) from None


def _validate_required(
    message_type: MessageType, fields: Mapping[str, Any]
) -> None:
    for name in MESSAGE_SPECS[message_type].required:
        if name not in fields or fields[name] is None:
            raise InvalidMessage(f"{message_type} requires the field {name!r}")


def encode(
    message_type: str | MessageType,
    *,
    version: int = PROTOCOL_VERSION,
    **fields: Any,
) -> dict[str, Any]:
    """Build a wire message.

    Validating on send makes host bugs fail at the call site instead of
    surfacing as a ``KeyError`` inside the pipe listener.
    """
    message_type = _coerce_type(message_type)

    reserved = RESERVED_FIELDS.intersection(fields)
    if reserved:
        raise InvalidMessage(
            f"Fields {sorted(reserved)} are part of the envelope and cannot be set"
        )

    if not isinstance(version, int) or isinstance(version, bool):
        raise InvalidMessage(f"Protocol version must be an int, got {version!r}")
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedVersion(version)

    _validate_required(message_type, fields)

    return {"v": version, "type": message_type.value, **fields}


@dataclasses.dataclass(frozen=True)
class Message:
    """A decoded, validated message."""

    type: MessageType
    version: int
    fields: Mapping[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.fields[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)

    def as_dict(self) -> dict[str, Any]:
        return {"v": self.version, "type": self.type.value, **self.fields}


def decode(
    raw: Any, *, supported_versions: Iterable[int] = SUPPORTED_VERSIONS
) -> Message:
    """Validate a wire message.

    Raises:
        InvalidMessage: not a mapping, no ``type``/``v``, or missing fields.
        UnknownMessageType: a type this protocol does not know.
        UnsupportedVersion: ``v`` is not in ``supported_versions``.
    """
    if not isinstance(raw, Mapping):
        raise InvalidMessage(
            f"Expected a mapping, got {type(raw).__name__}; the stream cannot be resynchronised"
        )

    if "type" not in raw:
        raise InvalidMessage("Message has no 'type' field")
    raw_type = raw["type"]
    if not isinstance(raw_type, str):
        raise InvalidMessage(f"Message 'type' must be a string, got {type(raw_type).__name__}")

    message_type = _coerce_type(raw_type)

    if "v" not in raw:
        raise InvalidMessage("Message has no protocol version field 'v'")
    version = raw["v"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise InvalidMessage(f"Protocol version must be an int, got {version!r}")

    supported = tuple(supported_versions)
    if version not in supported:
        raise UnsupportedVersion(version, supported)

    fields = {key: value for key, value in raw.items() if key not in RESERVED_FIELDS}
    _validate_required(message_type, fields)

    return Message(type=message_type, version=version, fields=fields)


def direction_of(message_type: str | MessageType) -> Direction:
    """Direction in which a message type is allowed to travel."""
    return MESSAGE_SPECS[_coerce_type(message_type)].direction


def negotiate_version(
    peer_min: int,
    peer_max: int,
    supported: Iterable[int] = SUPPORTED_VERSIONS,
) -> int:
    """Pick the highest protocol version both peers understand."""
    for value in (peer_min, peer_max):
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidMessage(f"Protocol versions must be ints, got {value!r}")

    if peer_min > peer_max:
        raise InvalidMessage(
            f"Reversed protocol range: min={peer_min} is greater than max={peer_max}"
        )

    supported = tuple(supported)
    common = sorted(set(supported).intersection(range(peer_min, peer_max + 1)))
    if not common:
        raise UnsupportedVersion(peer_min, supported)

    return common[-1]
