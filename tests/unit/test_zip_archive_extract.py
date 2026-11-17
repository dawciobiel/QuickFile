# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
ZIP extraction is part of the archive contract, and archive members must stay
inside the destination directory.

ZIP entries are just names from an untrusted file. ``../evil`` or an absolute
path would escape the directory the user picked, so the task validates every
target before writing. The regression this guards against is the classic
"zip slip" extraction bug.
"""

import importlib.util
import os
import zipfile

import pytest

from app.plugin_system.api import TaskCancelled
from tests.plugin_helpers import get_latest_plugin_path


class FakeContext:
    def __init__(self, cancelled=False):
        self.cancelled = cancelled
        self.progress_values = []

    def check_cancelled(self):
        if self.cancelled:
            raise TaskCancelled("Task was cancelled")

    def wait_if_paused(self):
        pass

    def progress(self, percentage):
        self.progress_values.append(percentage)


@pytest.fixture
def tasks_module():
    version_dir = get_latest_plugin_path("org.quickfile", "zip_archiver")
    spec = importlib.util.spec_from_file_location(
        "zip_tasks_under_test", os.path.join(version_dir, "tasks.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_zip(path, entries):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def test_extract_zip_writes_nested_files_and_reports_progress(tmp_path, tasks_module):
    source = tmp_path / "archive.zip"
    write_zip(
        source,
        {
            "file.txt": "hello",
            "nested/inner.txt": "world",
            "empty/": "",
        },
    )
    dest = tmp_path / "extracted"
    context = FakeContext()

    result = tasks_module.ExtractZipTask(
        str(source), str(dest), {}
    ).run(context)

    assert result == {"extract_path": str(dest)}
    assert (dest / "file.txt").read_text(encoding="utf-8") == "hello"
    assert (dest / "nested" / "inner.txt").read_text(encoding="utf-8") == "world"
    assert (dest / "empty").is_dir()
    assert context.progress_values[-1] == 100


@pytest.mark.parametrize(
    "member_name",
    [
        "../escape.txt",
        "nested/../../escape.txt",
        "..\\escape.txt",
    ],
)
def test_extract_zip_refuses_members_that_escape_the_destination(
    tmp_path, tasks_module, member_name
):
    source = tmp_path / "archive.zip"
    write_zip(source, {member_name: "evil"})
    dest = tmp_path / "extracted"

    with pytest.raises(ValueError, match="escapes"):
        tasks_module.ExtractZipTask(str(source), str(dest), {}).run(FakeContext())

    assert not (tmp_path / "escape.txt").exists()


def test_extract_zip_refuses_an_absolute_member_path(tmp_path, tasks_module):
    outside = tmp_path / "outside.txt"
    source = tmp_path / "archive.zip"
    write_zip(source, {str(outside): "evil"})

    with pytest.raises(ValueError, match="escapes"):
        tasks_module.ExtractZipTask(
            str(source), str(tmp_path / "extracted"), {}
        ).run(FakeContext())

    assert not outside.exists()


def test_extract_zip_stops_when_the_task_is_cancelled(tmp_path, tasks_module):
    source = tmp_path / "archive.zip"
    write_zip(source, {"file.txt": "hello"})
    dest = tmp_path / "extracted"

    with pytest.raises(TaskCancelled):
        tasks_module.ExtractZipTask(str(source), str(dest), {}).run(
            FakeContext(cancelled=True)
        )

    assert not (dest / "file.txt").exists()
