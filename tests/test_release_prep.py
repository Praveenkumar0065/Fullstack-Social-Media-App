import importlib.util
from pathlib import Path

import pytest


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "release_prep.py"
    spec = importlib.util.spec_from_file_location("release_prep", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_semver_validation():
    module = _load_module()
    module.ensure_semver("1.2.3")
    with pytest.raises(ValueError):
        module.ensure_semver("1.2")
    with pytest.raises(ValueError):
        module.ensure_semver("v1.2.3")


def test_bump_version_modes():
    module = _load_module()
    assert module.bump_version("1.2.3", "patch") == "1.2.4"
    assert module.bump_version("1.2.3", "minor") == "1.3.0"
    assert module.bump_version("1.2.3", "major") == "2.0.0"


def test_write_release_notes_force_behavior(tmp_path: Path):
    module = _load_module()
    notes = module.write_release_notes(tmp_path, "9.9.9", "## Summary\n", force=False)
    assert notes.exists()

    with pytest.raises(FileExistsError):
        module.write_release_notes(tmp_path, "9.9.9", "## Summary\n", force=False)

    overwritten = module.write_release_notes(tmp_path, "9.9.9", "## Summary\nUpdated\n", force=True)
    assert overwritten.read_text(encoding="utf-8") == "## Summary\nUpdated\n"


def test_read_version_validates_semver(tmp_path: Path):
    module = _load_module()
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    assert module.read_version(tmp_path) == "1.0.0"

    (tmp_path / "VERSION").write_text("invalid\n", encoding="utf-8")
    with pytest.raises(ValueError):
        module.read_version(tmp_path)
