"""Tests for the skill model."""

import pytest

from skillkit.model import SkillError, find_skills, is_name_valid, load_skill

VALID = """---
name: pdf-tools
description: Extracts text and tables from PDF files. Use when the user mentions PDFs.
---

Steps here.
"""


def make_skill(tmp_path, name="pdf-tools", content=VALID, folder=None):
    folder = folder or name
    root = tmp_path / folder
    root.mkdir()
    (root / "SKILL.md").write_text(content, encoding="utf-8")
    return root


def test_load_valid_skill(tmp_path):
    root = make_skill(tmp_path)
    skill = load_skill(root)
    assert skill.name == "pdf-tools"
    assert skill.description.startswith("Extracts text")
    assert skill.line_count == 2


def test_missing_folder_raises(tmp_path):
    with pytest.raises(SkillError):
        load_skill(tmp_path / "nope")


def test_missing_skill_md_raises(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(SkillError):
        load_skill(root)


def test_missing_name_raises(tmp_path):
    content = "---\ndescription: Something useful for agents.\n---\nbody"
    root = make_skill(tmp_path, content=content)
    with pytest.raises(SkillError):
        load_skill(root)


def test_missing_description_raises(tmp_path):
    content = "---\nname: x\n---\nbody"
    root = make_skill(tmp_path, folder="x", content=content)
    with pytest.raises(SkillError):
        load_skill(root)


def test_unclosed_frontmatter_raises(tmp_path):
    content = "---\nname: x\ndescription: y\n"
    root = make_skill(tmp_path, folder="x", content=content)
    with pytest.raises(SkillError):
        load_skill(root)


def test_name_validation_rules():
    assert is_name_valid("pdf-tools")
    assert is_name_valid("a")
    assert is_name_valid("web-scrape-2")
    assert not is_name_valid("PDF-Tools")          # uppercase
    assert not is_name_valid("-lead")              # leading hyphen
    assert not is_name_valid("trail-")             # trailing hyphen
    assert not is_name_valid("double--hyphen")
    assert not is_name_valid("has space")
    assert not is_name_valid("claude")             # reserved
    assert not is_name_valid("anthropic")          # reserved
    assert not is_name_valid("a" * 65)             # too long
    assert is_name_valid("a" * 64)


def test_find_skills_in_directory(tmp_path):
    make_skill(tmp_path, name="skill-a")
    make_skill(tmp_path, name="skill-b")
    # a broken one must be skipped, not raised
    broken = tmp_path / "broken"
    broken.mkdir()

    skills = find_skills(tmp_path)
    names = {s.path.name for s in skills}
    assert names == {"skill-a", "skill-b"}


def test_find_skills_on_single_skill_folder(tmp_path):
    root = make_skill(tmp_path)
    skills = find_skills(root)
    assert len(skills) == 1
    assert skills[0].name == "pdf-tools"


def test_find_skills_empty_dir(tmp_path):
    assert find_skills(tmp_path) == []
