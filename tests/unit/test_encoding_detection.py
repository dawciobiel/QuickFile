# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Encoding detection shared by the viewer and other text readers."""

import codecs

from utils.encoding import detect_encoding


def test_plain_utf8_is_detected():
    assert detect_encoding("Zażółć".encode("utf-8")) == "utf-8"


def test_utf8_bom_wins_over_plain_utf8():
    data = codecs.BOM_UTF8 + "hello".encode("utf-8")

    assert detect_encoding(data) == "utf-8-sig"


def test_utf16_bom_is_detected():
    assert detect_encoding("hello".encode("utf-16")) == "utf-16"


def test_utf32_bom_is_detected():
    assert detect_encoding("hello".encode("utf-32")) == "utf-32"


def test_windows_1250_is_detected_for_polish_text():
    data = "Zażółć gęślą jaźń".encode("windows-1250")

    assert detect_encoding(data) == "windows-1250"


def test_iso_8859_2_is_used_when_cp1250_cannot_decode():
    # 0x81 is undefined in Windows-1250 and Windows-1252.
    assert detect_encoding(b"\x81") == "iso-8859-2"
