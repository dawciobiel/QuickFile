# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Detect the encoding of text files without extra dependencies.

The order is deliberate: a byte order mark is authoritative, then UTF-8, then
the encoding preferred by the operating system, then the single-byte encodings
commonly used for Polish and Western European text. Latin-1 accepts every byte,
so it is the last resort and never fails.
"""

import codecs
import locale

DEFAULT_ENCODING = "utf-8"

#: Codecs offered by the viewer's encoding selector.
COMMON_ENCODINGS = (
    "utf-8",
    "utf-8-sig",
    "utf-16",
    "utf-32",
    "windows-1250",
    "windows-1252",
    "iso-8859-2",
    "latin-1",
)


def detect_encoding(data: bytes) -> str:
    """Return the most likely encoding of ``data``."""
    if data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return "utf-32"
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"

    candidates = (
        "utf-8",
        locale.getpreferredencoding(False),
        "windows-1250",
        "windows-1252",
        "iso-8859-2",
        "latin-1",
    )
    seen = set()
    for candidate in candidates:
        if not candidate or candidate.lower() in seen:
            continue
        seen.add(candidate.lower())
        try:
            data.decode(candidate)
        except (UnicodeDecodeError, LookupError):
            continue
        return candidate
    return "latin-1"
