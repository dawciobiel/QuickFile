# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Publishing packages is an explicit, idempotent release step.

Re-running a failed release must not upload a second copy or silently replace
an asset that changed: the first would fail on GitHub, the second would hide
that the package differs from what was tested. The decision logic lives in
``scripts/publish_plugin_packages.py``; ``gh`` is only the transport.

Specification: ``docs/architecture/plugins/plugins.md`` ("Publikacja paczek").
"""

import hashlib
import json
import os
import subprocess

import pytest

import scripts.publish_plugin_packages as publisher
from scripts.publish_plugin_packages import PublishError, publish_packages


def digest(content):
    return hashlib.sha256(content).hexdigest()


def make_package(directory, name="zip_archiver-1.0.4.zip", content=b"package"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path


class FakeGh:
    def __init__(self, assets=None, release_exists=True):
        self.assets = assets or {}
        self.release_exists = release_exists
        self.uploads = []
        self.created = []
        self.downloads = []
        self.contents = {}

    def release_assets(self, tag):
        if not self.release_exists:
            raise PublishError(f"release {tag} not found")
        return dict(self.assets)

    def create_release(self, tag):
        self.created.append(tag)
        self.release_exists = True

    def upload_asset(self, tag, path):
        self.uploads.append((tag, os.path.basename(path)))

    def download_asset(self, tag, name, directory):
        self.downloads.append((tag, name))
        path = os.path.join(directory, name)
        with open(path, "wb") as handle:
            handle.write(self.contents[name])
        return path


def test_missing_assets_are_uploaded(tmp_path):
    package = make_package(tmp_path / "dist")
    gh = FakeGh()

    actions = publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.uploads == [("v1", package.name)]
    assert [(action.kind, action.name) for action in actions] == [
        ("upload", package.name)
    ]


def test_an_identical_asset_is_skipped_by_digest(tmp_path):
    package = make_package(tmp_path / "dist")
    content = package.read_bytes()
    gh = FakeGh(
        assets={
            package.name: {
                "name": package.name,
                "size": len(content),
                "digest": f"sha256:{digest(content)}",
            }
        }
    )

    actions = publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.uploads == []
    assert gh.downloads == []
    assert actions[0].kind == "skip"


def test_an_asset_with_different_bytes_is_refused(tmp_path):
    package = make_package(tmp_path / "dist")
    gh = FakeGh(
        assets={
            package.name: {
                "name": package.name,
                "size": len(package.read_bytes()),
                "digest": f"sha256:{digest(b'other bytes')}",
            }
        }
    )

    with pytest.raises(PublishError, match="refusing to replace"):
        publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.uploads == []


def test_without_a_digest_the_asset_is_downloaded_and_compared(tmp_path):
    package = make_package(tmp_path / "dist")
    content = package.read_bytes()
    gh = FakeGh(
        assets={package.name: {"name": package.name, "size": len(content)}}
    )
    gh.contents[package.name] = content

    actions = publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.downloads == [("v1", package.name)]
    assert gh.uploads == []
    assert actions[0].kind == "skip"


def test_without_a_digest_different_bytes_are_refused(tmp_path):
    package = make_package(tmp_path / "dist")
    gh = FakeGh(
        assets={
            package.name: {
                "name": package.name,
                "size": len(package.read_bytes()),
            }
        }
    )
    gh.contents[package.name] = b"different package"

    with pytest.raises(PublishError, match="refusing to replace"):
        publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.uploads == []


def test_dry_run_reports_but_does_not_upload(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh()

    actions = publish_packages(
        "v1", [tmp_path / "dist"], gh, dry_run=True
    )

    assert [action.kind for action in actions] == ["upload"]
    assert gh.uploads == []


def test_a_missing_release_is_an_error_without_create_release(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh(release_exists=False)

    with pytest.raises(PublishError, match="release"):
        publish_packages("v1", [tmp_path / "dist"], gh)

    assert gh.uploads == []


def test_create_release_publishes_when_the_release_is_missing(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh(release_exists=False)

    actions = publish_packages(
        "v1", [tmp_path / "dist"], gh, create_release=True
    )

    assert gh.created == ["v1"]
    assert [action.kind for action in actions] == ["create", "upload"]
    assert len(gh.uploads) == 1


def test_dry_run_does_not_create_a_release(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh(release_exists=False)

    actions = publish_packages(
        "v1", [tmp_path / "dist"], gh, dry_run=True, create_release=True
    )

    assert gh.created == []
    assert [action.kind for action in actions] == ["create", "upload"]


def test_duplicate_package_names_are_refused(tmp_path):
    make_package(tmp_path / "one")
    make_package(tmp_path / "two")

    with pytest.raises(PublishError, match="Duplicate package name"):
        publish_packages("v1", [tmp_path / "one", tmp_path / "two"], FakeGh())


def test_an_empty_package_set_is_an_error(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(PublishError, match="No .zip"):
        publish_packages("v1", [empty], FakeGh())


def test_a_missing_package_directory_is_an_error(tmp_path):
    with pytest.raises(PublishError, match="not found"):
        publish_packages("v1", [tmp_path / "missing"], FakeGh())


def test_the_cli_prints_the_plan(tmp_path, capsys):
    package = make_package(tmp_path / "dist")
    gh = FakeGh()

    exit_code = publisher.main(
        ["--tag", "v1", "--packages", str(tmp_path / "dist"), "--dry-run"],
        client=gh,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "would upload" in output
    assert package.name in output


def test_the_cli_returns_one_on_a_refused_release(tmp_path, capsys):
    make_package(tmp_path / "dist")
    gh = FakeGh(release_exists=False)

    exit_code = publisher.main(
        ["--tag", "v1", "--packages", str(tmp_path / "dist")],
        client=gh,
    )

    assert exit_code == 1
    assert "release" in capsys.readouterr().err


def test_the_gh_client_reads_the_release_assets():
    calls = []

    def runner(args):
        calls.append(args)
        return json.dumps(
            {"assets": [{"name": "zip-1.0.0.zip", "size": 4, "digest": "sha256:ab"}]}
        )

    client = publisher.GhClient(repo="owner/repo", runner=runner)

    assets = client.release_assets("v1")

    assert calls == [
        ["release", "view", "v1", "--repo", "owner/repo", "--json", "assets"]
    ]
    assert assets["zip-1.0.0.zip"]["digest"] == "sha256:ab"


def test_the_gh_client_uploads_with_the_repository():
    calls = []

    def runner(args):
        calls.append(args)
        return ""

    client = publisher.GhClient(repo="owner/repo", runner=runner)

    client.upload_asset("v1", "/tmp/zip-1.0.0.zip")

    assert calls == [
        [
            "release",
            "upload",
            "v1",
            "/tmp/zip-1.0.0.zip",
            "--repo",
            "owner/repo",
        ]
    ]


def test_the_gh_client_creates_a_release_for_an_existing_tag():
    calls = []

    def runner(args):
        calls.append(args)
        return ""

    client = publisher.GhClient(repo="owner/repo", runner=runner)

    client.create_release("v1")

    assert calls[0][:4] == ["release", "create", "v1", "--repo"]
    assert "--verify-tag" in calls[0]


def test_the_gh_client_reports_a_failed_command(monkeypatch):
    def fake_run(command, capture_output, text):
        return subprocess.CompletedProcess(command, 1, "", "boom")

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    client = publisher.GhClient(repo="owner/repo")

    with pytest.raises(PublishError, match="boom"):
        client.release_assets("v1")


def test_the_gh_client_fails_when_the_download_is_missing(tmp_path):
    client = publisher.GhClient(runner=lambda args: "")

    with pytest.raises(PublishError, match="did not download"):
        client.download_asset("v1", "zip-1.0.0.zip", str(tmp_path))
