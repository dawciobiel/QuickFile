# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Host binaries required by plugins.

A plugin can declare packages in ``metadata.json``, but some libraries are only
wrappers around a program in the host system: ``rarfile`` needs ``unrar``,
``unar``, ``bsdtar`` or ``7z``. The host cannot ship those binaries, so it has
to say so before a task is queued instead of failing halfway through.

This module validates the declaration and resolves the executables. It stays
Qt-free and side-effect free: it never installs, downloads or runs a tool.
"""

import shutil
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class ExternalToolsError(ValueError):
    """Raised when a plugin's ``external_tools`` declaration is invalid."""


@dataclass(frozen=True)
class ToolRequirement:
    """One program a plugin needs, satisfiable by any listed command."""

    id: str
    name: str
    executables: Tuple[str, ...]


@dataclass(frozen=True)
class ToolStatus:
    """Result of resolving a requirement against the host."""

    requirement: ToolRequirement
    executable: Optional[str]

    @property
    def available(self) -> bool:
        return self.executable is not None


def requirements_for(metadata: Optional[Dict[str, Any]]) -> List[ToolRequirement]:
    """Return the validated requirements declared by ``metadata``.

    An absent declaration means "no tools". A malformed one raises, because a
    declaration the host cannot read also cannot tell whether the plugin will
    work.
    """
    declaration = (metadata or {}).get("external_tools")
    if declaration is None:
        return []

    if not isinstance(declaration, list):
        raise ExternalToolsError("external_tools must be a list")

    requirements = []
    seen = set()
    for index, entry in enumerate(declaration):
        requirement = _parse_entry(index, entry)
        if requirement.id in seen:
            raise ExternalToolsError(
                f"external_tools entry {index} reuses id {requirement.id!r}"
            )
        seen.add(requirement.id)
        requirements.append(requirement)
    return requirements


def check_tools(
    metadata: Optional[Dict[str, Any]], which=None
) -> List[ToolStatus]:
    """Resolve every declared requirement against ``PATH``.

    ``which`` is injectable so callers and tests do not depend on the machine.
    """
    which = which or shutil.which
    statuses = []
    for requirement in requirements_for(metadata):
        executable = None
        for candidate in requirement.executables:
            executable = which(candidate)
            if executable:
                break
        statuses.append(ToolStatus(requirement, executable))
    return statuses


def missing_tools(
    metadata: Optional[Dict[str, Any]], which=None
) -> List[ToolStatus]:
    """Return only the requirements no candidate satisfied."""
    return [
        status
        for status in check_tools(metadata, which=which)
        if not status.available
    ]


def _parse_entry(index: int, entry: Any) -> ToolRequirement:
    label = f"external_tools entry {index}"
    if not isinstance(entry, dict):
        raise ExternalToolsError(f"{label} must be an object")

    tool_id = entry.get("id")
    if not isinstance(tool_id, str) or not tool_id:
        raise ExternalToolsError(f"{label} must have a non-empty id")

    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise ExternalToolsError(f"{label} must have a non-empty name")

    executables = entry.get("executables")
    if not isinstance(executables, list) or not executables:
        raise ExternalToolsError(f"{label} must list at least one executable")

    for executable in executables:
        _validate_executable(label, executable)

    return ToolRequirement(tool_id, name, tuple(executables))


def _validate_executable(label: str, executable: Any) -> None:
    if not isinstance(executable, str) or not executable.strip():
        raise ExternalToolsError(
            f"{label} has an executable that is not a non-empty string"
        )
    # Command names only: a path would bake one machine's layout into metadata
    # and bypass PATH lookup on every other platform.
    if "/" in executable or "\\" in executable:
        raise ExternalToolsError(
            f"{label} must use command names, not paths: {executable!r}"
        )
