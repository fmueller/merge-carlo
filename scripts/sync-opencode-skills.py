#!/usr/bin/env python3
"""Expose Amp User Skills to OpenCode through runtime-only symlinks."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn, cast
from urllib.parse import unquote, urlparse

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPO_ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> NoReturn:
    print(f"OpenCode skill sync failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def amp_user_skills() -> dict[str, Path]:
    environment = os.environ.copy()
    environment.pop("ZAI_API_KEY", None)
    environment.pop("ZHIPU_API_KEY", None)
    try:
        result = subprocess.run(
            ["amp", "skill", "list", "--json"],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
            timeout=8,
        )
        payload = cast(object, json.loads(result.stdout))
    except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
        fail("Amp's authenticated User Skills inventory is unavailable")

    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        fail("Amp returned an unsupported skills inventory")

    skills: dict[str, Path] = {}
    for raw_entry in cast(list[object], payload["skills"]):
        if not isinstance(raw_entry, dict):
            continue
        entry = cast(dict[str, object], raw_entry)
        if entry.get("source") != "global-user":
            continue
        raw_name = entry.get("name")
        raw_base_dir = entry.get("baseDir")
        if not isinstance(raw_name, str) or not SKILL_NAME.fullmatch(raw_name) or not isinstance(raw_base_dir, str):
            fail("Amp returned invalid User Skill metadata")
        name = raw_name
        base_dir = raw_base_dir
        parsed = urlparse(base_dir)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            fail("Amp returned a User Skill outside its local runtime cache")
        source = Path(unquote(parsed.path))
        if not source.is_absolute() or not source.is_dir() or not (source / "SKILL.md").is_file():
            fail("an Amp User Skill is not materialized in this orb")
        if name in skills:
            fail("Amp returned duplicate User Skill metadata")
        skills[name] = source
    return skills


def load_manifest(path: Path) -> dict[str, str]:
    if path.is_symlink():
        fail("the runtime link manifest must not be a symlink")
    try:
        payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        fail("the runtime link manifest is unreadable")
    if not isinstance(payload, dict):
        fail("the runtime link manifest is invalid")
    manifest: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not SKILL_NAME.fullmatch(key) or not isinstance(value, str):
            fail("the runtime link manifest is invalid")
        if not Path(value).is_absolute():
            fail("the runtime link manifest is invalid")
        manifest[key] = value
    return manifest


def write_manifest(path: Path, links: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as manifest:
            descriptor = -1
            manifest.write(json.dumps(links, sort_keys=True) + "\n")
        temporary.replace(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def points_to(path: Path, target: str) -> bool:
    return path.is_symlink() and os.readlink(path) == target


def sync() -> int:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    if not config_home.is_absolute() or not state_home.is_absolute():
        fail("XDG configuration and state paths must be absolute")
    if config_home.resolve().is_relative_to(REPO_ROOT) or state_home.resolve().is_relative_to(REPO_ROOT):
        fail("OpenCode runtime paths must be outside the repository")
    destination = config_home / "opencode" / "skills"
    manifest_path = state_home / "merge-carlo" / "opencode-user-skill-links.json"
    previous = load_manifest(manifest_path)
    requested = amp_user_skills()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)

    for name, stale_target in previous.items():
        link = destination / name
        if name not in requested and points_to(link, stale_target):
            link.unlink()

    managed: dict[str, str] = {}
    conflicts = 0
    for name, source in requested.items():
        link = destination / name
        target = str(source)
        if os.path.lexists(link):
            if points_to(link, target):
                managed[name] = target
                continue
            previous_target = previous.get(name)
            if previous_target is None or not points_to(link, previous_target):
                conflicts += 1
                continue
            link.unlink()
        try:
            link.symlink_to(source, target_is_directory=True)
        except FileExistsError:
            conflicts += 1
            continue
        managed[name] = target

    write_manifest(manifest_path, managed)
    if conflicts:
        fail(f"{conflicts} destination path(s) are user-managed; no files were overwritten")
    return len(managed)


def main() -> None:
    quiet = sys.argv[1:] == ["--quiet"]
    if sys.argv[1:] not in ([], ["--quiet"]):
        fail("usage: sync-opencode-skills.py [--quiet]")
    count = sync()
    if not quiet:
        print(f"Linked {count} Amp User Skill(s) for OpenCode")


if __name__ == "__main__":
    main()
