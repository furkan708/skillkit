"""skillkit — the toolbox for AI agent skills (SKILL.md) with a built-in MCP server."""

from .linter import Finding, LintReport, lint_skill
from .model import Skill, SkillError, find_skills, load_skill

__version__ = "1.0.2"
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
