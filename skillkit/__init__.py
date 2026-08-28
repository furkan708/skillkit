"""skillkit — the toolbox for AI agent skills (SKILL.md) with a built-in MCP server."""

from .model import Skill, SkillError, find_skills, load_skill
from .linter import LintReport, Finding, lint_skill

__version__ = "1.0.0"
__all__ = [
    "Skill",
    "SkillError",
    "find_skills",
    "load_skill",
    "LintReport",
    "Finding",
    "lint_skill",
    "__version__",
]
