# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Shutdown behaviour of the host runtime.

The application stops plugins from ``QApplication.aboutToQuit``, but that is
not the only way a process ends: an exception, ``sys.exit()`` or a test session
can finish with plugin processes still running. A listener thread that logs or
emits Qt signals at that moment used to abort the process with ``SIGABRT``
(``Fatal Python error: _enter_buffered_busy``), hiding the real exit code.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import textwrap
from unittest import mock

import pytest

import app.plugin_system.host as host_module
from app.plugin_system.host import SandboxedPluginWrapper

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DUMMY_PLUGIN_SOURCE = os.path.join(PROJECT_ROOT, "tests", "dummy_plugin.py")


def _write_plugin(directory):
    version_dir = os.path.join(directory, "org.quickfile", "dummy", "0.1.0")
    os.makedirs(version_dir)
    shutil.copyfile(DUMMY_PLUGIN_SOURCE, os.path.join(version_dir, "plugin.py"))

    metadata = {
        "id": "org.quickfile.dummy",
        "name": "Dummy Plugin",
        "version": "0.1.0",
        "author": "QuickFile Team",
        "type": "checksum",
        "description": "Deterministic plugin used by the runtime tests.",
        "entry_point": "plugin:DummyPlugin",
        "class_name": "DummyPlugin",
        "sandboxed": True,
        "platforms": ["linux", "windows", "macos"],
    }
    with open(os.path.join(version_dir, "metadata.json"), "w", encoding="utf-8") as handle:
        json.dump(metadata, handle)

    return version_dir, metadata


@pytest.fixture
def unstarted_wrapper(tmp_path, qapp):
    path, metadata = _write_plugin(str(tmp_path / "plugins"))
    return SandboxedPluginWrapper(path, metadata)


def _run_host_script(tmp_path, body):
    path, metadata = _write_plugin(str(tmp_path / "plugins"))
    script = tmp_path / "host_script.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import sys

            from app.plugin_system.host import SandboxedPluginWrapper

            wrapper = SandboxedPluginWrapper({path!r}, {metadata!r})
            wrapper.start()
            """
        )
        + textwrap.dedent(body),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    # A script run by path does not get the working directory on sys.path.
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [PROJECT_ROOT, env.get("PYTHONPATH", "")])
    )
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_the_interpreter_exits_cleanly_when_a_plugin_was_never_stopped(tmp_path):
    """End to end: a live plugin at exit must not become SIGABRT."""
    result = _run_host_script(tmp_path, "assert wrapper.is_ready()\nsys.exit(0)\n")

    assert result.returncode == 0, result.stderr
    assert "Fatal Python error" not in result.stderr


def test_safe_log_writes_nothing_while_the_interpreter_finalizes(
    unstarted_wrapper, caplog, monkeypatch
):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(host_module.sys, "is_finalizing", lambda: True)

    unstarted_wrapper._safe_log("warning", "must not reach a closed stream")

    assert "must not reach a closed stream" not in caplog.text


def test_safe_log_swallows_closed_stream_errors(unstarted_wrapper, monkeypatch):
    logger = mock.Mock()
    logger.warning.side_effect = ValueError("I/O operation on closed file")
    monkeypatch.setattr(unstarted_wrapper, "logger", logger)

    unstarted_wrapper._safe_log("warning", "ignored")  # must not raise

    logger.warning.assert_called_once()


def test_emit_tolerates_a_deleted_wrapper(unstarted_wrapper):
    """A thread can outlive its QObject; emitting then raises RuntimeError."""

    class DeletedSignal:
        def emit(self, *args):
            raise RuntimeError(
                "wrapped C/C++ object of type SandboxedPluginWrapper has been deleted"
            )

    unstarted_wrapper._emit(DeletedSignal(), "task-1", 42)  # must not raise
