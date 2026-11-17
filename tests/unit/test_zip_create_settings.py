# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""ZIP settings use the names from the metadata schema, not zipfile constants."""

import importlib.util
import os
import zipfile

import pytest

from app.plugin_system.api import TaskCancelled
from tests.plugin_helpers import get_latest_plugin_path


class FakeContext:
    def check_cancelled(self):
        pass

    def wait_if_paused(self):
        pass

    def progress(self, percentage):
        pass


@pytest.fixture
def tasks_module():
    version_dir = get_latest_plugin_path("org.quickfile", "zip_archiver")
    spec = importlib.util.spec_from_file_location(
        "zip_create_tasks_under_test", os.path.join(version_dir, "tasks.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create(tmp_path, tasks_module, options):
    source = tmp_path / "file.txt"
    source.write_text("hello" * 100, encoding="utf-8")
    archive = tmp_path / "archive.zip"

    tasks_module.CreateZipTask(
        [str(source)], str(archive), options
    ).run(FakeContext())
    return archive


def test_the_store_method_writes_an_uncompressed_archive(tmp_path, tasks_module):
    archive = create(tmp_path, tasks_module, {"compression": "store"})

    with zipfile.ZipFile(archive) as zipf:
        assert zipf.infolist()[0].compress_type == zipfile.ZIP_STORED


def test_the_default_method_is_deflate(tmp_path, tasks_module):
    archive = create(tmp_path, tasks_module, {})

    with zipfile.ZipFile(archive) as zipf:
        assert zipf.infolist()[0].compress_type == zipfile.ZIP_DEFLATED


def test_an_unknown_method_is_rejected(tmp_path, tasks_module):
    with pytest.raises(ValueError, match="compression"):
        create(tmp_path, tasks_module, {"compression": "lzma"})


def test_cancelled_creation_writes_nothing(tmp_path, tasks_module):
    class CancelledContext(FakeContext):
        def check_cancelled(self):
            raise TaskCancelled("Task was cancelled")

    source = tmp_path / "file.txt"
    source.write_text("hello", encoding="utf-8")
    archive = tmp_path / "archive.zip"

    with pytest.raises(TaskCancelled):
        tasks_module.CreateZipTask(
            [str(source)], str(archive), {}
        ).run(CancelledContext())

    assert not archive.exists()
