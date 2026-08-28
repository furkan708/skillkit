"""Skill model: load and inspect SKILL.md skill folders.

Implements the Agent Skills open specification (agentskills.io):
a skill is a directory whose entry point is a SKILL.md file with
``name`` and ``description`` frontmatter plus a Markdown body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import FrontmatterError, parse_skill_document

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
BODY_LINES_RECOMMENDED = 500
RESERVED_WORDS = {"anthropic", "claude"}
SKILL_FILE = "SKILL.md"

# Optional folders defined by the specification.
SPEC_FOLDERS = ("scripts", "references", "assets")

# Common folder-name mistakes we flag in lint.
FOLDER_TYPOS = {
    "script": "scripts",
    "reference": "references",
    "asset": "assets",
    "doc": "references",
    "docs": "references",
    "utils": "scripts",
}


class SkillError(ValueError):
    """Raised when a skill folder cannot be loaded."""


@dataclass
class Skill:
    """A loaded skill folder."""

    path: Path
    name: str
    description: str
    body: str
    frontmatter: dict = field(default_factory=dict)

    @property
    def line_count(self) -> int:
        return len(self.body.splitlines())

    @property
    def body_chars(self) -> int:
        return len(self.body)

    def extra_files(self) -> list[Path]:
        """All files in the folder except SKILL.md itself."""
        return sorted(
            p for p in self.path.rglob("*") if p.is_file() and p.name != SKILL_FILE
        )


def is_name_valid(name: str) -> bool:
    return (
        bool(name)
        and len(name) <= NAME_MAX
        and bool(NAME_PATTERN.match(name))
        and name not in RESERVED_WORDS
    )


def load_skill(path: str | Path) -> Skill:
    """Load and validate the structure of a skill folder.

    Structural errors (no SKILL.md, unparseable frontmatter, missing
    required fields) raise :class:`SkillError`. Spec *violations* that
    still allow loading (bad name charset, over-long description) are
    returned as-is for the linter to report.
    """
    folder = Path(path)
    skill_file = folder / SKILL_FILE
    if not folder.is_dir():
        raise SkillError(f"not a directory: {folder}")
    if not skill_file.is_file():
        raise SkillError(f"missing {SKILL_FILE} in {folder}")

    text = skill_file.read_text(encoding="utf-8")
    try:
        data, body = parse_skill_document(text)
    except FrontmatterError as err:
        raise SkillError(f"{skill_file}: {err}") from err
    if not isinstance(data, dict):
        raise SkillError(f"{skill_file}: frontmatter must be a mapping")

    name = data.get("name", "")
    description = data.get("description", "")
    if not isinstance(name, str) or not name.strip():
        raise SkillError(f"{skill_file}: frontmatter field 'name' is required")
    if not isinstance(description, str) or not description.strip():
        raise SkillError(f"{skill_file}: frontmatter field 'description' is required")

    return Skill(
        path=folder,
        name=name.strip(),
        description=description.strip(),
        body=body,
        frontmatter=data,
    )


def find_skills(directory: str | Path) -> list[Skill]:
    """Find all loadable skills inside a directory (one level deep).

    Also accepts *directory* itself being a skill folder. Broken skills
    are skipped silently — use :func:`load_skill` directly for details.
    """
    root = Path(directory)
    if not root.is_dir():
        return []
    if (root / SKILL_FILE).is_file():
        try:
            return [load_skill(root)]
        except SkillError:
            return []
    skills: list[Skill] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / SKILL_FILE).is_file():
            try:
                skills.append(load_skill(child))
            except SkillError:
                continue
    return skills
