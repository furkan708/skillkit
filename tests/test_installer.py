"""Tests for install / list / remove flows."""

import pytest

from skillkit.installer import (
    install_from_git,
    install_skill,
    list_installed,
    remove_skill,
    resolve_target,
)
from skillkit.model import SkillError
from skillkit.scaffold import new_skill


@pytest.fixture()
def skill(tmp_path):
    return new_skill(
        tmp_path / "src",
        "test-skill",
        "Installs cleanly into agent skill directories. Use when testing installs.",
    )


def test_install_and_list(tmp_path, skill):
    target = tmp_path / "installed"
    folder = install_skill(skill, target)
    assert (folder / "SKILL.md").is_file()

    entries = list_installed(target)
    assert len(entries) == 1
    assert entries[0]["name"] == "test-skill"
    assert entries[0]["description"].startswith("Installs cleanly")


def test_install_requires_valid_skill(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    with pytest.raises(SkillError):
        install_skill(broken, tmp_path / "installed")


def test_install_refuses_duplicate(tmp_path, skill):
    target = tmp_path / "installed"
    install_skill(skill, target)
    with pytest.raises(SkillError):
        install_skill(skill, target)


def test_remove_skill(tmp_path, skill):
    target = tmp_path / "installed"
    install_skill(skill, target)
    removed = remove_skill("test-skill", target)
    assert not removed.exists()
    with pytest.raises(SkillError):
        remove_skill("test-skill", target)


def test_list_reports_broken_skills(tmp_path, skill):
    target = tmp_path / "installed"
    install_skill(skill, target)
    broken = target / "broken-skill"
    broken.mkdir()  # no SKILL.md

    entries = list_installed(target)
    by_name = {e["name"]: e for e in entries}
    assert "error" in by_name["broken-skill"]
    assert "description" in by_name["test-skill"]


def test_resolve_target_defaults_to_claude(monkeypatch):
    monkeypatch.setattr("skillkit.installer.Path", __import__("pathlib").Path)
    assert resolve_target(None, None).name == "skills"
    assert "claude" in str(resolve_target("claude", None))
    assert resolve_target(None, "/custom/path") == __import__("pathlib").Path("/custom/path")


def test_install_from_git_local_repo(tmp_path, skill):
    import subprocess

    # build a local git repo containing the skill at its root
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.io"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    subprocess.run(["cp", "-r", str(skill), str(repo / "test-skill")], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "skill"], check=True)

    target = tmp_path / "installed"
    installed = install_from_git(str(repo), target)
    assert len(installed) == 1
    assert installed[0].name == "test-skill"
    assert (installed[0] / "SKILL.md").is_file()


def test_install_from_git_repo_without_skills(tmp_path):
    import subprocess

    repo = tmp_path / "empty-repo"
    repo.mkdir()
    (repo / "readme.txt").write_text("not a skill", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.io"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

    with pytest.raises(SkillError):
        install_from_git(str(repo), tmp_path / "installed")
