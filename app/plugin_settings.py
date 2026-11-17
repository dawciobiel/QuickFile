# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Host-side contract for plugin settings.

A plugin declares settings in ``metadata.json``; the host renders the form.
This module validates that declaration and normalises values. It intentionally
does not import Qt: schema handling is testable without a QApplication, and the
same rules can later be used before a task is queued.

The supported vocabulary is deliberately small. Anything richer (conditional
fields, custom widgets) belongs in a future host page, not in an ad-hoc GUI
language hidden inside plugin metadata.
"""

from typing import Any, Dict, Optional

FIELD_TYPES = frozenset({"string", "integer", "boolean", "enum"})


class PluginSettingsError(ValueError):
    """Raised when settings metadata or an option value is invalid."""


def schema_for_plugin(plugin) -> Optional[Dict[str, Any]]:
    """Return the plugin's ``settings.schema`` or ``None``.

    Metadata is read directly because a sandboxed plugin exposes methods, not
    arbitrary attributes. The schema is returned unvalidated so a broken
    metadata block cannot stop the plugin from being used; callers that render
    it validate first.
    """
    metadata = getattr(plugin, "metadata", None) or {}
    settings = metadata.get("settings") or {}
    schema = settings.get("schema")
    return schema or None


def validate_schema(schema: Dict[str, Any]) -> None:
    """Check that ``schema`` only uses the supported field vocabulary."""
    if not isinstance(schema, dict):
        raise PluginSettingsError("Settings schema must be an object")

    for name, field in schema.items():
        if not isinstance(name, str) or not name:
            raise PluginSettingsError("Setting names must be non-empty strings")
        _validate_field(name, field)


def defaults_for(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return the default value of every field, validated."""
    return normalize_options(schema, {})


def normalize_options(
    schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Fill defaults and validate values, preserving unknown keys.

    Unknown keys are kept so upgrading the host does not discard settings that
    a newer plugin version already wrote.
    """
    validate_schema(schema)
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise PluginSettingsError("Plugin options must be an object")

    normalized = dict(options)
    for name, field in schema.items():
        value = options.get(name, field["default"])
        _validate_value(name, field, value)
        normalized[name] = value
    return normalized


def _validate_field(name: str, field: Any) -> None:
    if not isinstance(field, dict):
        raise PluginSettingsError(f"Setting {name!r} must be an object")

    field_type = field.get("type")
    if field_type not in FIELD_TYPES:
        raise PluginSettingsError(
            f"Setting {name!r} has unknown type {field_type!r}; "
            f"expected one of {sorted(FIELD_TYPES)}"
        )

    title = field.get("title")
    if not isinstance(title, str) or not title:
        raise PluginSettingsError(f"Setting {name!r} must have a title")

    if "default" not in field:
        raise PluginSettingsError(f"Setting {name!r} must have a default")

    if field_type == "integer":
        for bound in ("minimum", "maximum"):
            if bound in field and not _is_integer(field[bound]):
                raise PluginSettingsError(
                    f"Setting {name!r} has a non-integer {bound}"
                )
        minimum = field.get("minimum")
        maximum = field.get("maximum")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise PluginSettingsError(
                f"Setting {name!r} has minimum greater than maximum"
            )

    if field_type == "enum":
        choices = field.get("choices")
        if not isinstance(choices, list) or not choices:
            raise PluginSettingsError(
                f"Setting {name!r} must have a non-empty choices list"
            )
        values = set()
        for choice in choices:
            if not isinstance(choice, dict):
                raise PluginSettingsError(
                    f"Setting {name!r} has a choice that is not an object"
                )
            value = choice.get("value")
            label = choice.get("label")
            if not isinstance(value, str) or not isinstance(label, str) or not label:
                raise PluginSettingsError(
                    f"Setting {name!r} choices need string value and label"
                )
            values.add(value)
        default = field["default"]
        if not isinstance(default, str) or default not in values:
            raise PluginSettingsError(
                f"Setting {name!r} default is not one of its choices"
            )

    _validate_value(name, field, field["default"])


def _validate_value(name: str, field: Dict[str, Any], value: Any) -> None:
    field_type = field["type"]

    if field_type == "string":
        if not isinstance(value, str):
            raise PluginSettingsError(f"Setting {name!r} must be a string")
        return

    if field_type == "boolean":
        if not isinstance(value, bool):
            raise PluginSettingsError(f"Setting {name!r} must be a boolean")
        return

    if field_type == "integer":
        if not _is_integer(value):
            raise PluginSettingsError(f"Setting {name!r} must be an integer")
        minimum = field.get("minimum")
        maximum = field.get("maximum")
        if minimum is not None and value < minimum:
            raise PluginSettingsError(
                f"Setting {name!r} must be at least {minimum}"
            )
        if maximum is not None and value > maximum:
            raise PluginSettingsError(
                f"Setting {name!r} must be at most {maximum}"
            )
        return

    values = {choice["value"] for choice in field["choices"]}
    if not isinstance(value, str) or value not in values:
        raise PluginSettingsError(
            f"Setting {name!r} must be one of {sorted(values)}"
        )


def _is_integer(value: Any) -> bool:
    # bool is an int subclass; True must not be accepted as 1.
    return isinstance(value, int) and not isinstance(value, bool)
