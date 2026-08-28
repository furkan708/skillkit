"""skillkit command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .installer import (
    AGENT_DIRS,
    install_from_git,
    install_skill,
    list_installed,
    remove_skill,
    resolve_target,
)
from .linter import format_report, lint_skill
from .model import SkillError
from .scaffold import new_skill, pack_skill

USE_COLOR = sys.stdout.isatty()


def _fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="skillkit",
        description=(
            "The toolbox for AI agent skills: scaffold, lint, pack, install, "
            "and serve SKILL.md skills — with a built-in MCP server."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="scaffold a new skill folder")
    p_new.add_argument("name", help="skill name (lowercase-hyphens, must match folder)")
    p_new.add_argument("-d", "--description", required=True, help="what it does + when to use it")
    p_new.add_argument("--dir", default=".", help="where to create the folder (default: cwd)")

    p_lint = sub.add_parser("lint", help="validate a skill (spec + security + quality)")
    p_lint.add_argument("path", help="path to the skill folder")
    p_lint.add_argument("--json", action="store_true", help="output machine-readable JSON")
    p_lint.add_argument("--strict", action="store_true", help="exit 1 on warnings too")

    p_pack = sub.add_parser("pack", help="zip a skill for upload")
    p_pack.add_argument("path", help="path to the skill folder")
    p_pack.add_argument("-o", "--output", help="output zip path (default: <name>.zip)")

    p_install = sub.add_parser("install", help="install a skill from a folder or git URL")
    p_install.add_argument("source", help="skill folder path or git repository URL")
    p_install.add_argument(
        "--agent",
        choices=sorted(AGENT_DIRS),
        default="claude",
        help="install target (default: claude)",
    )
    p_install.add_argument("--dir", dest="dir_override", help="override the target directory")

    p_list = sub.add_parser("list", help="list installed skills")
    p_list.add_argument("--agent", choices=sorted(AGENT_DIRS), default="claude")
    p_list.add_argument("--dir", dest="dir_override", help="override the target directory")
    p_list.add_argument("--json", action="store_true", help="output machine-readable JSON")

    p_rm = sub.add_parser("remove", help="remove an installed skill")
    p_rm.add_argument("name", help="skill folder name")
    p_rm.add_argument("--agent", choices=sorted(AGENT_DIRS), default="claude")
    p_rm.add_argument("--dir", dest="dir_override", help="override the target directory")

    p_mcp = sub.add_parser("mcp", help="serve installed skills over MCP (stdio)")
    p_mcp.add_argument("--agent", choices=sorted(AGENT_DIRS), default="claude")
    p_mcp.add_argument("--dir", dest="dir_override", help="override the skills directory")

    args = parser.parse_args(argv)

    if args.command == "new":
        try:
            folder = new_skill(args.dir, args.name, args.description)
        except ValueError as err:
            _fail(str(err))
        print(f"created {folder}/")
        print(f"next:  skillkit lint {folder}")

    elif args.command == "lint":
        report = lint_skill(args.path)
        if args.json:
            print(
                json.dumps(
                    {
                        "skill": report.skill_name,
                        "score": report.score,
                        "grade": report.grade,
                        "ok": report.ok,
                        "findings": [
                            {"rule": f.rule, "severity": f.severity, "message": f.message}
                            for f in report.findings
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(format_report(report, use_color=USE_COLOR))
        if report.errors or (args.strict and report.warnings):
            sys.exit(1)

    elif args.command == "pack":
        try:
            zip_path = pack_skill(args.path, args.output)
        except (ValueError, SkillError) as err:
            _fail(str(err))
        print(f"packed: {zip_path}")

    elif args.command == "install":
        target = resolve_target(args.agent, args.dir_override)
        try:
            if args.source.startswith(("http://", "https://", "git@")):
                installed = install_from_git(args.source, target)
                for folder in installed:
                    print(f"installed: {folder}")
            else:
                folder = install_skill(args.source, target)
                print(f"installed: {folder}")
        except (SkillError, ValueError) as err:
            _fail(str(err))
        except Exception as err:  # git failures etc.
            _fail(f"could not install from '{args.source}': {err}")

    elif args.command == "list":
        directory = resolve_target(args.agent, args.dir_override)
        entries = list_installed(directory)
        if args.json:
            print(
                json.dumps(
                    [
                        {**e, "path": str(e["path"])}
                        for e in entries
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if not entries:
            print(f"no skills installed in {directory}")
            return
        print(f"skills in {directory}:")
        for entry in entries:
            if "error" in entry:
                print(f"  ✗ {entry['name']} — broken: {entry['error']}")
            else:
                print(
                    f"  • {entry['name']:24} {entry['lines']:4} lines · "
                    f"{entry['files']:2} files · {entry['description'][:60]}"
                )

    elif args.command == "remove":
        directory = resolve_target(args.agent, args.dir_override)
        try:
            folder = remove_skill(args.name, directory)
        except SkillError as err:
            _fail(str(err))
        print(f"removed: {folder}")

    elif args.command == "mcp":
        from .mcp_server import main as serve

        directory = resolve_target(args.agent, args.dir_override)
        if not directory.is_dir():
            print(
                f"note: skills directory {directory} does not exist yet "
                "(tools will return empty results)",
                file=sys.stderr,
            )
        serve(directory)


if __name__ == "__main__":
    main()
