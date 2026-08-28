"""Tests for scaffolding and packing."""

import zipfile

import pytest

from skillkit.model import load_skill
from skillkit.scaffold import new_skill, pack_skill


def test_new_skill_creates_spec_layout(tmp_path):
    folder = new_skill(
        tmp_path,
        "commit-writer",
        "Writes conventional commits from diffs. Use when committing changes.",
    )
    assert (folder / "SKILL.md").is_file()
    assert (folder / "references").is_dir()
    assert (folder / "scripts").is_dir()
    assert (folder / "README.md").is_file()


def test_new_skill_lints_clean(tmp_path):
    from skillkit.linter import lint_skill

    folder = new_skill(
        tmp_path,
        "commit-writer",
        "Writes conventional commit messages from staged diffs. "
        "Use when the user asks to commit changes.",
    )
    report = lint_skill(folder)
    assert report.ok, report.findings


def test_new_skill_loads_and_matches_name(tmp_path):
    folder = new_skill(tmp_path, "pdf-tools", "Extracts text from PDF files on demand.")
    skill = load_skill(folder)
    assert skill.name == "pdf-tools"


def test_new_skill_rejects_bad_name(tmp_path):
    with pytest.raises(ValueError):
        new_skill(tmp_path, "Bad Name", "A description long enough.")


def test_new_skill_refuses_overwrite(tmp_path):
    new_skill(tmp_path, "dup", "A description long enough to pass.")
    with pytest.raises(ValueError):
        new_skill(tmp_path, "dup", "A description long enough to pass.")


def test_pack_creates_zip_with_folder_prefix(tmp_path):
    folder = new_skill(tmp_path, "zip-me", "Packs and ships skill folders safely.")
    zip_path = pack_skill(folder)
    assert zip_path.name == "zip-me.zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "zip-me/SKILL.md" in names
        assert "zip-me/references/usage.md" in names


def test_pack_custom_output(tmp_path):
    folder = new_skill(tmp_path, "out", "Writes output files to custom locations.")
    zip_path = pack_skill(folder, tmp_path / "custom.zip")
    assert zip_path.name == "custom.zip"


def test_pack_rejects_non_skill(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    with pytest.raises(ValueError):
        pack_skill(broken)
