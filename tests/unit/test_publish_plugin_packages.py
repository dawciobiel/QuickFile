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
import zipfile

import pytest

import scripts.publish_plugin_packages as publisher
from scripts.publish_plugin_packages import PublishError, publish_packages


def digest(content):
    return hashlib.sha256(content).hexdigest()


def make_package(
    directory,
    name="zip_archiver-1.0.4.zip",
    content=b"package",
    plugin_id=None,
    version=None,
    metadata=True,
):
    """Build a package shaped like ``build_plugin_package.py`` output.

    ``metadata`` is ``True`` for metadata derived from the name, a dict to
    write verbatim, a string to write the metadata under that archive path, or
    ``False`` to omit it entirely.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    artifact_id, _, name_version = name[: -len(".zip")].rpartition("-")
    if plugin_id is None:
        plugin_id = f"org.quickfile.{artifact_id}"
    if version is None:
        version = name_version

    entries = {"plugin.py": content}
    if metadata is True or isinstance(metadata, str):
        target = "metadata.json" if metadata is True else metadata
        entries[target] = json.dumps({"id": plugin_id, "version": version}).encode()
    elif isinstance(metadata, dict):
        entries["metadata.json"] = json.dumps(metadata).encode()

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry_name in sorted(entries):
            info = zipfile.ZipInfo(entry_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, entries[entry_name])
    return path


class FakeGh:
    def __init__(self, assets=None, release_exists=True):
        self.assets = assets or {}
        self.release_exists = release_exists
        self.uploads = []
        self.uploaded = {}
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
        name = os.path.basename(path)
        self.uploads.append((tag, name))
        with open(path, "rb") as handle:
            self.uploaded[name] = handle.read()

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

    assert gh.uploads == [("v1", package.name), ("v1", "plugin-index.json")]
    assert [(action.kind, action.name) for action in actions] == [
        ("upload", package.name),
        ("upload", "plugin-index.json"),
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

    assert gh.uploads == [("v1", "plugin-index.json")]
    assert gh.downloads == []
    assert [action.kind for action in actions] == ["skip", "upload"]


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
    assert gh.uploads == [("v1", "plugin-index.json")]
    assert [action.kind for action in actions] == ["skip", "upload"]


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

    assert [action.kind for action in actions] == ["upload", "upload"]
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
    assert [action.kind for action in actions] == ["create", "upload", "upload"]
    assert len(gh.uploads) == 2


def test_dry_run_does_not_create_a_release(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh(release_exists=False)

    actions = publish_packages(
        "v1", [tmp_path / "dist"], gh, dry_run=True, create_release=True
    )

    assert gh.created == []
    assert [action.kind for action in actions] == ["create", "upload", "upload"]


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


def read_index(gh):
    return json.loads(gh.uploaded["plugin-index.json"])


def test_the_index_describes_the_uploaded_packages(tmp_path):
    package = make_package(
        tmp_path / "dist", name="rar_archiver-1.0.4.zip", content=b"rar"
    )
    gh = FakeGh()

    publish_packages("v1", [tmp_path / "dist"], gh)

    assert read_index(gh) == {
        "schema_version": 1,
        "packages": [
            {
                "id": "org.quickfile.rar_archiver",
                "version": "1.0.4",
                "file": "rar_archiver-1.0.4.zip",
                "sha256": digest(package.read_bytes()),
                "size": package.stat().st_size,
            }
        ],
    }


def test_the_index_is_uploaded_after_every_package(tmp_path):
    make_package(tmp_path / "dist", name="zip_archiver-1.0.4.zip")
    gh = FakeGh()

    publish_packages("v1", [tmp_path / "dist"], gh)

    assert [name for _, name in gh.uploads] == [
        "zip_archiver-1.0.4.zip",
        "plugin-index.json",
    ]


def test_the_index_is_sorted_by_id_then_numeric_version(tmp_path):
    make_package(tmp_path / "dist", name="zeta-1.0.9.zip")
    make_package(tmp_path / "dist", name="zeta-1.0.10.zip")
    make_package(
        tmp_path / "dist", name="alpha-2.0.0.zip", plugin_id="org.quickfile.alpha"
    )
    gh = FakeGh()

    publish_packages("v1", [tmp_path / "dist"], gh)

    entries = read_index(gh)["packages"]
    assert [(entry["id"], entry["version"]) for entry in entries] == [
        ("org.quickfile.alpha", "2.0.0"),
        ("org.quickfile.zeta", "1.0.9"),
        ("org.quickfile.zeta", "1.0.10"),
    ]


def test_the_index_is_byte_identical_for_the_same_packages(tmp_path):
    make_package(tmp_path / "dist", name="zeta-1.0.9.zip")
    make_package(tmp_path / "dist", name="alpha-2.0.0.zip")
    second = FakeGh()
    first = FakeGh()

    publish_packages("v1", [tmp_path / "dist"], first)
    publish_packages("v1", [tmp_path / "dist"], second)

    assert first.uploaded["plugin-index.json"] == second.uploaded["plugin-index.json"]


def test_the_index_uses_metadata_inside_the_package(tmp_path):
    make_package(
        tmp_path / "dist",
        name="renamed-1.0.4.zip",
        plugin_id="org.quickfile.rar_archiver",
        version="1.0.4",
    )

    with pytest.raises(PublishError, match="does not match metadata"):
        publish_packages("v1", [tmp_path / "dist"], FakeGh())


def test_a_package_without_metadata_is_refused(tmp_path):
    make_package(tmp_path / "dist", metadata=False)

    with pytest.raises(PublishError, match="no metadata.json"):
        publish_packages("v1", [tmp_path / "dist"], FakeGh())


def test_a_nested_metadata_file_is_not_accepted(tmp_path):
    make_package(tmp_path / "dist", metadata="nested/metadata.json")

    with pytest.raises(PublishError, match="no metadata.json"):
        publish_packages("v1", [tmp_path / "dist"], FakeGh())


def test_invalid_metadata_is_refused(tmp_path):
    make_package(tmp_path / "dist", metadata={"id": "org.quickfile.zip_archiver"})

    with pytest.raises(PublishError, match="version"):
        publish_packages("v1", [tmp_path / "dist"], FakeGh())


def test_a_non_numeric_version_is_refused(tmp_path):
    make_package(
        tmp_path / "dist", name="zip_archiver-1.0.4.zip", version="latest"
    )

    with pytest.raises(PublishError, match="not a valid version"):
        publish_packages("v1", [tmp_path / "dist"], FakeGh())


def test_an_identical_index_is_skipped(tmp_path):
    package = make_package(tmp_path / "dist")
    gh = FakeGh()
    publish_packages("v1", [tmp_path / "dist"], gh)
    index = gh.uploaded["plugin-index.json"]

    existing = FakeGh(
        assets={
            "plugin-index.json": {
                "name": "plugin-index.json",
                "size": len(index),
                "digest": f"sha256:{digest(index)}",
            }
        }
    )
    actions = publish_packages("v1", [tmp_path / "dist"], existing)

    assert existing.uploads == [("v1", package.name)]
    assert [action.kind for action in actions] == ["upload", "skip"]
    assert actions[-1].name == "plugin-index.json"


def test_a_different_published_index_is_refused(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh(
        assets={
            "plugin-index.json": {
                "name": "plugin-index.json",
                "size": 2,
                "digest": f"sha256:{digest(b'{}')}",
            }
        }
    )

    with pytest.raises(PublishError, match="refusing to replace"):
        publish_packages("v1", [tmp_path / "dist"], gh)


def test_dry_run_plans_the_index_but_does_not_upload_it(tmp_path):
    make_package(tmp_path / "dist")
    gh = FakeGh()

    actions = publish_packages("v1", [tmp_path / "dist"], gh, dry_run=True)

    assert gh.uploads == []
    assert [action.name for action in actions] == [
        "zip_archiver-1.0.4.zip",
        "plugin-index.json",
    ]
