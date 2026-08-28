"""Linter for Agent Skills: spec violations, security smells, quality score.

Motivated by real-world data: audits of community skill repositories show
the overwhelming majority of published SKILL.md files carry at least one
"skill smell", and a large share carry security issues such as hardcoded
secrets. This linter catches the common ones before you publish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .model import (
    BODY_LINES_RECOMMENDED,
    DESCRIPTION_MAX,
    FOLDER_TYPOS,
    NAME_MAX,
    RESERVED_WORDS,
    SPEC_FOLDERS,
    Skill,
    is_name_valid,
    load_skill,
)

ERROR = "error"
WARN = "warn"
INFO = "info"

_VAGUE_STARTS = ("helps", "a tool", "basic", "useful", "various", "stuff")

# Well-known credential shapes; keep patterns conservative to avoid noise.
SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OpenAI-style key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "Hardcoded credential assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*"
            r"['\"]?[A-Za-z0-9+/_-]{16,}"
        ),
    ),
]


@dataclass
class Finding:
    rule: str
    severity: str  # ERROR | WARN | INFO
    message: str

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        icon = {"error": "✗", "warn": "⚠", "info": "·"}[self.severity]
        return f"{icon} [{self.rule}] {self.message}"


@dataclass
class LintReport:
    skill_name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == WARN]

    @property
    def infos(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == INFO]

    @property
    def score(self) -> int:
        penalty = 25 * len(self.errors) + 10 * len(self.warnings)
        return max(0, 100 - penalty)

    @property
    def grade(self) -> str:
        score = self.score
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 50:
            return "C"
        return "D"

    @property
    def ok(self) -> bool:
        return not self.errors


def lint_skill(path: str | Path) -> LintReport:
    """Lint a skill folder and return the full report."""
    skill: Skill | None = None
    report = LintReport(skill_name=Path(path).name)

    try:
        skill = load_skill(path)
    except Exception as err:  # SkillError or frontmatter issues
        report.findings.append(
            Finding("SKILL000", ERROR, f"skill cannot be loaded: {err}")
        )
        report.skill_name = Path(path).name
        return report

    report.skill_name = skill.name
    data = skill.frontmatter

    # --- name field -----------------------------------------------------
    if not is_name_valid(skill.name):
        problems = []
        if len(skill.name) > NAME_MAX:
            problems.append(f"longer than {NAME_MAX} characters")
        if skill.name in RESERVED_WORDS:
            problems.append(f"reserved word '{skill.name}' is not allowed")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill.name):
            problems.append(
                "must be lowercase letters, numbers and hyphens only "
                "(no leading/trailing hyphen)"
            )
        report.findings.append(
            Finding("SKILL001", ERROR, f"invalid name '{skill.name}': {'; '.join(problems)}")
        )
    if skill.name != skill.path.name:
        report.findings.append(
            Finding(
                "SKILL002",
                ERROR,
                f"name '{skill.name}' does not match folder name '{skill.path.name}'",
            )
        )

    # --- description field ----------------------------------------------
    if len(skill.description) > DESCRIPTION_MAX:
        report.findings.append(
            Finding(
                "SKILL003",
                ERROR,
                f"description is {len(skill.description)} characters "
                f"(max {DESCRIPTION_MAX})",
            )
        )
    lowered = skill.description.lower()
    if len(skill.description) < 40 or lowered.startswith(_VAGUE_STARTS):
        report.findings.append(
            Finding(
                "SKILL004",
                WARN,
                "description is vague — describe what the skill does AND when "
                "to use it, with concrete keywords agents can match",
            )
        )

    # --- body -------------------------------------------------------------
    if skill.line_count > BODY_LINES_RECOMMENDED:
        report.findings.append(
            Finding(
                "SKILL005",
                WARN,
                f"body has {skill.line_count} lines (recommended max "
                f"{BODY_LINES_RECOMMENDED}) — move detail into references/",
            )
        )
    if skill.line_count < 10:
        report.findings.append(
            Finding("SKILL006", INFO, "body is very thin — add steps and examples")
        )

    # --- security: secrets --------------------------------------------------
    full_text = (skill.path / "SKILL.md").read_text(encoding="utf-8")
    for label, pattern in SECRET_PATTERNS:
        match = pattern.search(full_text)
        if match:
            report.findings.append(
                Finding(
                    "SEC001",
                    ERROR,
                    f"possible {label} found in SKILL.md: '{match.group(0)[:12]}…' — "
                    "move secrets to environment variables",
                )
            )

    # --- folder hygiene -----------------------------------------------------
    present = {p.name for p in skill.path.iterdir() if p.is_dir()}
    for name in sorted(present):
        if name in FOLDER_TYPOS:
            report.findings.append(
                Finding(
                    "SKILL007",
                    WARN,
                    f"folder '{name}/' looks like a typo of '{FOLDER_TYPOS[name]}/' "
                    "(spec-defined folders: " + ", ".join(SPEC_FOLDERS) + ")",
                )
            )

    # --- frontmatter hygiene ------------------------------------------------
    known = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    for key in data:
        if key not in known:
            report.findings.append(
                Finding(
                    "SKILL008",
                    INFO,
                    f"unknown frontmatter field '{key}' (spec-compliant agents ignore it)",
                )
            )
    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        report.findings.append(
            Finding("SKILL009", ERROR, "'metadata' must be a string-to-string map")
        )

    return report


def format_report(report: LintReport, use_color: bool = True) -> str:
    """Human-readable multi-line report for the terminal."""

    def colorize(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if use_color else text

    lines = [colorize(f"skillkit lint: {report.skill_name}", "1")]
    if not report.findings:
        lines.append(colorize("  ✓ no issues found", "32"))
    for f in report.findings:
        style = {"error": "31", "warn": "33", "info": "36"}[f.severity]
        lines.append("  " + colorize(str(f), style))
    grade_color = "32" if report.grade in "AB" else ("33" if report.grade == "C" else "31")
    lines.append("")
    lines.append(
        f"  score: {colorize(str(report.score), grade_color + ';1')}/100 "
        f"(grade {colorize(report.grade, grade_color)}) · "
        f"{len(report.errors)} errors · {len(report.warnings)} warnings · "
        f"{len(report.infos)} notes"
    )
    return "\n".join(lines)
