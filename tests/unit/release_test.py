import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "pyproject.toml").is_file():
    ROOT = ROOT.parent


def _workflow(name: str) -> dict[str, Any]:
    document = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return cast(dict[str, Any], document)


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], job["steps"])


def _step_index(steps: list[dict[str, Any]], name: str) -> int:
    for index, step in enumerate(steps):
        if step.get("name") == name:
            return index
    raise AssertionError(f"workflow step not found: {name}")


def _gate_script(workflow_name: str, step_name: str) -> str:
    workflow = _workflow(workflow_name)
    jobs = cast(dict[str, Any], workflow["jobs"])
    steps = _steps(cast(dict[str, Any], jobs["build"]))
    run = next(step["run"] for step in steps if step.get("name") == step_name)
    marker = "python - <<'PY'\n"
    assert marker in run
    return cast(str, run.split(marker, 1)[1].split("\nPY", 1)[0])


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _release_fixture(tmp_path: Path, *, tag_on_main: bool = True) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "config", "user.email", "release-test@example.invalid")
    (repository / "pyproject.toml").write_text('[project]\nname = "merge-carlo"\nversion = "0.1.0"\n', encoding="utf-8")
    _git(repository, "add", "pyproject.toml")
    _git(repository, "commit", "-m", "fixture")
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "main")
    if tag_on_main:
        _git(repository, "tag", "v0.1.0")
    else:
        (repository / "marker").write_text("moved tag\n", encoding="utf-8")
        _git(repository, "add", "marker")
        _git(repository, "commit", "-m", "moved tag")
        _git(repository, "tag", "v0.1.0")
    _git(repository, "checkout", "--detach", "v0.1.0")
    return repository


def _run_gate(script: str, repository: Path, **environment: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **environment}
    return subprocess.run([sys.executable, "-c", script], cwd=repository, env=env, capture_output=True, text=True)


@pytest.mark.unit
def test_release_metadata_has_a_dated_versioned_section_and_evidence_status() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE)
    release_section = changelog.split(f"## [{version}] - ", 1)[1].split("\n## ", 1)[0]
    assert "Live GitHub integration has not been run." in release_section
    assert "No authorized dataset was" in release_section


@pytest.mark.unit
def test_mutation_runner_copies_repository_files_used_by_the_suite() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    also_copy = set(project["tool"]["mutmut"]["also_copy"])

    assert {"README.md", "CHANGELOG.md", ".github/", "docs/", "examples/"} <= also_copy


@pytest.mark.unit
def test_release_workflows_are_tokenless_and_gate_the_versioned_artifact() -> None:
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    test_index = (ROOT / ".github" / "workflows" / "test-index.yml").read_text(encoding="utf-8")

    assert "types: [published]" in release
    assert "workflow_dispatch:" in test_index
    for workflow_text in (release, test_index):
        assert "pypa/gh-action-pypi-publish@" in workflow_text
        assert "id-token: write" in workflow_text
        assert "twine check dist/*" in workflow_text
        assert "sha256sum --check" in workflow_text
        assert "username:" not in workflow_text
        assert "password:" not in workflow_text
    assert "environment:\n      name: pypi" in release
    assert "environment:\n      name: testpypi" in test_index
    assert "RELEASE_TAG" in release and "RELEASE_TAG" in test_index
    assert "Live GitHub integration has not been run." in release
    release_notes = (ROOT / "docs" / "release-notes-v0.1.0.md").read_text(encoding="utf-8")
    assert "Live GitHub integration has not been run." in release_notes

    for name in ("release.yml", "test-index.yml"):
        workflow = _workflow(name)
        jobs = cast(dict[str, Any], workflow["jobs"])
        build_steps = _steps(cast(dict[str, Any], jobs["build"]))
        publish_job = cast(dict[str, Any], jobs["publish"])
        publish_steps = _steps(publish_job)
        assert publish_job["needs"] == "build"
        assert publish_job["permissions"]["id-token"] == "write"

        upload = next(step for step in build_steps if str(step.get("uses", "")).startswith("actions/upload-artifact@"))
        download = next(
            step for step in publish_steps if str(step.get("uses", "")).startswith("actions/download-artifact@")
        )
        assert upload["with"]["name"] == download["with"]["name"]
        assert "dist/" in upload["with"]["path"]
        assert "SHA256SUMS" in upload["with"]["path"]

        checksum_index = _step_index(publish_steps, "Verify the distribution checksums")
        publish_name = "Publish package distributions to PyPI"
        if name == "test-index.yml":
            publish_name = "Publish package distributions to TestPyPI"
        publish_index = _step_index(publish_steps, publish_name)
        assert checksum_index < publish_index
        assert "sha256sum --check" in publish_steps[checksum_index]["run"]
        publish_action = publish_steps[publish_index]
        assert re.search(r"pypa/gh-action-pypi-publish@[0-9a-f]{40}", publish_action["uses"])
        if name == "test-index.yml":
            assert publish_action["with"]["repository-url"] == "https://test.pypi.org/legacy/"
        else:
            assert "repository-url" not in publish_action["with"]
        download_path = download["with"]["path"]
        assert download_path == "release-bundle"
        assert publish_action["with"]["packages-dir"] == f"{download_path}/dist"

        identity_name = "Verify release identity and evidence notes"
        if name == "test-index.yml":
            identity_name = "Verify tag, source identity, and package version"
        identity_index = _step_index(build_steps, identity_name)
        dependency_index = _step_index(build_steps, "Install locked dependencies")
        assert identity_index < dependency_index
        identity_run = build_steps[identity_index]["run"]
        assert "SystemExit" in identity_run
        assert "origin/main" in identity_run
        assert "does not match package version" in identity_run
        if name == "release.yml":
            assert "Live GitHub integration has not been run." in identity_run
            assert "No authorized dataset was" in identity_run


@pytest.mark.unit
def test_release_identity_gate_rejects_missing_evidence(tmp_path: Path) -> None:
    repository = _release_fixture(tmp_path)
    result = _run_gate(
        _gate_script("release.yml", "Verify release identity and evidence notes"),
        repository,
        RELEASE_TAG="v0.1.0",
        RELEASE_PRERELEASE="false",
        RELEASE_NOTES="missing evidence",
    )

    assert result.returncode != 0
    assert "live integration was not run" in result.stderr


@pytest.mark.unit
def test_test_index_identity_gate_rejects_a_tag_not_on_main(tmp_path: Path) -> None:
    repository = _release_fixture(tmp_path, tag_on_main=False)
    result = _run_gate(
        _gate_script("test-index.yml", "Verify tag, source identity, and package version"),
        repository,
        RELEASE_TAG="v0.1.0",
    )

    assert result.returncode != 0
    assert "current origin/main commit" in result.stderr
