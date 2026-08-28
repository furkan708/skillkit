"""A zero-dependency MCP (Model Context Protocol) server for skills.

Speaks newline-delimited JSON-RPC 2.0 over stdio, as used by MCP stdio
transports. Lets any MCP client (Claude Code, Cursor, and friends) list,
read, and lint the skills installed on this machine.

Run with: ``skillkit mcp`` (or ``skillkit mcp --dir ./skills``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .linter import lint_skill
from .model import SkillError, find_skills, load_skill

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "skillkit"
SERVER_VERSION = "1.0.0"

TOOLS = [
    {
        "name": "list_skills",
        "description": (
            "List the AI agent skills installed on this machine, with name, "
            "description, and size. Use this to discover available expertise."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_skill",
        "description": (
            "Read the full SKILL.md instructions of one installed skill. "
            "Use after list_skills when a skill looks relevant to the task."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill folder name"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "lint_skill",
        "description": (
            "Validate an installed skill against the Agent Skills "
            "specification and return issues plus a quality score."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill folder name"}
            },
            "required": ["name"],
        },
    },
]


class SkillkitServer:
    """JSON-RPC handler implementing the MCP tools surface."""

    def __init__(self, skills_dir: str | Path) -> None:
        self.skills_dir = Path(skills_dir).expanduser()

    # ------------------------------------------------------------------
    # tool implementations (return JSON-serializable payloads)
    # ------------------------------------------------------------------
    def tool_list_skills(self, _arguments: dict):
        skills = find_skills(self.skills_dir)
        return {
            "skills_dir": str(self.skills_dir),
            "count": len(skills),
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "folder": s.path.name,
                    "body_lines": s.line_count,
                }
                for s in skills
            ],
        }

    def tool_read_skill(self, arguments: dict):
        name = str(arguments.get("name", ""))
        folder = self.skills_dir / name
        if not (folder / "SKILL.md").is_file():
            raise SkillError(f"no skill named '{name}' in {self.skills_dir}")
        skill = load_skill(folder)
        return {
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.body,
        }

    def tool_lint_skill(self, arguments: dict):
        name = str(arguments.get("name", ""))
        folder = self.skills_dir / name
        if not (folder / "SKILL.md").is_file():
            raise SkillError(f"no skill named '{name}' in {self.skills_dir}")
        report = lint_skill(folder)
        return {
            "skill": report.skill_name,
            "score": report.score,
            "grade": report.grade,
            "ok": report.ok,
            "findings": [
                {"rule": f.rule, "severity": f.severity, "message": f.message}
                for f in report.findings
            ],
        }

    # ------------------------------------------------------------------
    # JSON-RPC dispatch
    # ------------------------------------------------------------------
    def _result(self, request_id, payload):
        return {"jsonrpc": "2.0", "id": request_id, "result": payload}

    def _error(self, request_id, code: int, message: str):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def handle_message(self, message: dict) -> dict | None:
        """Handle one decoded JSON-RPC message. Returns a response or None."""
        method = message.get("method", "")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            requested = params.get("protocolVersion", PROTOCOL_VERSION)
            return self._result(
                request_id,
                {
                    "protocolVersion": requested,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            )

        if method.startswith("notifications/"):
            return None  # notifications are never answered

        if method == "ping":
            return self._result(request_id, {})

        if method == "tools/list":
            return self._result(request_id, {"tools": TOOLS})

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}
            try:
                if tool_name == "list_skills":
                    payload = self.tool_list_skills(arguments)
                elif tool_name == "read_skill":
                    payload = self.tool_read_skill(arguments)
                elif tool_name == "lint_skill":
                    payload = self.tool_lint_skill(arguments)
                else:
                    return self._error(request_id, -32601, f"unknown tool: {tool_name}")
            except SkillError as err:
                return self._result(
                    request_id,
                    {
                        "content": [{"type": "text", "text": str(err)}],
                        "isError": True,
                    },
                )
            return self._result(
                request_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}
                    ]
                },
            )

        return self._error(request_id, -32601, f"method not found: {method}")

    def serve(self, stdin=None, stdout=None) -> None:
        """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
        input_stream = stdin if stdin is not None else sys.stdin
        output_stream = stdout if stdout is not None else sys.stdout
        for line in input_stream:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response = self._error(None, -32700, "parse error")
            else:
                response = self.handle_message(message)
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
                output_stream.flush()


def main(skills_dir: str | Path) -> None:
    SkillkitServer(skills_dir).serve()
