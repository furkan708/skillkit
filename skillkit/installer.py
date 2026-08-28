"""Install skills into agent skill directories and list installed skills."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .model import SKILL_FILE, SkillError, find_skills, load_skill

# Default install roots per agent. The Agent Skills standard is supported by
# 40+ platforms; these cover the most common CLI agents today.
AGENT_DIRS = {
    "claude": Path.home() / ".claude" / "skills",
    "project": Path("skills"),
}


def resolve_target(agent: str | None, dir_override: str | None) -> Path:
    if dir_override:
        return Path(dir_override).expanduser()
    return AGENT_DIRS.get(agent or "claude", AGENT_DIRS["claude"])


def install_skill(source: str | Path, target_dir: str | Path, name: str | None = None) -> Path:
    """Copy a skill folder into ``target_dir``.

    Args:
        source: Path to a skill folder (must contain SKILL.md).
        target_dir: Destination directory (created if missing).
        name: Optional new name for the installed folder.

    Returns:
        Path of the installed skill folder.
    """
    skill = load_skill(source)  # validates structure before installing
    destination = Path(target_dir) / (name or skill.path.name)
    if destination.exists():
        raise SkillError(f"already installed: {destination} (remove it first)")
    shutil.copytree(skill.path, destination)
    return destination


def install_from_git(repo_url: str, target_dir: str | Path) -> list[Path]:
    """Clone a git repository and install every skill found inside it.

    A repository may contain a single skill at its root or multiple skills
    in first-level folders. Returns the list of installed folders.
    """
    installed: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", repo_url, tmp],
            check=True,
        )
        root = Path(tmp)
        if (root / SKILL_FILE).is_file():
            candidates = [root]
        else:
            candidates = [
                child for child in sorted(root.iterdir())
                if child.is_dir() and (child / SKILL_FILE).is_file()
            ]
        if not candidates:
            raise SkillError(f"no skills (SKILL.md folders) found in {repo_url}")
        for candidate in candidates:
            installed.append(install_skill(candidate, target_dir))
    return installed


def list_installed(directory: str | Path) -> list[dict]:
    """Summarize the skills installed in a directory.

    Broken skills are reported with an 'error' entry instead of being
    raised, so one bad skill does not hide the rest.
    """
    results: list[dict] = []
    root = Path(directory)
    if not root.is_dir():
        return results
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        try:
            skill = load_skill(child)
        except SkillError as err:
            results.append({"name": child.name, "path": child, "error": str(err)})
            continue
        results.append(
            {
                "name": skill.name,
                "path": child,
                "description": skill.description,
                "lines": skill.line_count,
                "files": len(skill.extra_files()) + 1,
            }
        )
    return results


def remove_skill(name: str, directory: str | Path) -> Path:
    """Remove an installed skill folder by folder name."""
    target = Path(directory) / name
    if not target.is_dir() or not (target / SKILL_FILE).is_file():
        raise SkillError(f"no skill named '{name}' in {directory}")
    shutil.rmtree(target)
    return target


def skills_search_path(directory: str | Path) -> list:
    """Convenience wrapper around :func:`find_skills`."""
    return find_skills(directory)
