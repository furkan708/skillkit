"""Tests for the MCP server (JSON-RPC over stdio)."""

import json

import pytest

from skillkit.mcp_server import PROTOCOL_VERSION, SERVER_NAME, SkillkitServer
from skillkit.scaffold import new_skill


@pytest.fixture()
def server(tmp_path):
    new_skill(
        tmp_path,
        "demo-skill",
        "Demonstrates the MCP tools surface. Use when testing the server.",
    )
    return SkillkitServer(tmp_path)


def rpc(method, params=None, request_id=1):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def test_initialize_returns_capabilities(server):
    response = server.handle_message(
        rpc("initialize", {"protocolVersion": "2025-03-26"})
    )
    assert response["result"]["protocolVersion"] == "2025-03-26"
    assert response["result"]["capabilities"]["tools"] == {}
    assert response["result"]["serverInfo"]["name"] == SERVER_NAME


def test_initialize_default_protocol(server):
    response = server.handle_message(rpc("initialize", {}))
    assert response["result"]["protocolVersion"] == PROTOCOL_VERSION


def test_notifications_are_not_answered(server):
    assert server.handle_message(rpc("notifications/initialized")) is None


def test_ping_returns_empty_result(server):
    response = server.handle_message(rpc("ping"))
    assert response["result"] == {}


def test_tools_list_exposes_three_tools(server):
    response = server.handle_message(rpc("tools/list"))
    names = {t["name"] for t in response["result"]["tools"]}
    assert names == {"list_skills", "read_skill", "lint_skill"}


def test_list_skills_tool(server):
    response = server.handle_message(rpc("tools/call", {"name": "list_skills"}))
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["count"] == 1
    assert payload["skills"][0]["name"] == "demo-skill"


def test_read_skill_tool(server):
    response = server.handle_message(rpc("tools/call", {"name": "read_skill", "arguments": {"name": "demo-skill"}}))
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["name"] == "demo-skill"
    assert "instructions" in payload


def test_read_unknown_skill_is_tool_error(server):
    response = server.handle_message(rpc("tools/call", {"name": "read_skill", "arguments": {"name": "nope"}}))
    assert response["result"]["isError"] is True


def test_lint_skill_tool(server):
    response = server.handle_message(rpc("tools/call", {"name": "lint_skill", "arguments": {"name": "demo-skill"}}))
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["grade"] in "ABCD"
    assert payload["ok"] is True


def test_unknown_method_is_protocol_error(server):
    response = server.handle_message(rpc("resources/list"))
    assert response["error"]["code"] == -32601


def test_unknown_tool_is_protocol_error(server):
    response = server.handle_message(rpc("tools/call", {"name": "explode"}))
    assert response["error"]["code"] == -32601


def test_serve_loop_over_streams(server):
    stdin = iter(
        [
            json.dumps(rpc("initialize", {}, request_id=1)),
            json.dumps(rpc("notifications/initialized")),
            json.dumps(rpc("tools/list", request_id=2)),
            "",
            "not json",
            json.dumps(rpc("tools/call", {"name": "list_skills"}, request_id=3)),
        ]
    )
    import io

    out = io.StringIO()
    server.serve(stdin=stdin, stdout=out)
    lines = [json.loads(line) for line in out.getvalue().splitlines()]

    assert len(lines) == 4  # notifications and parse errors (with id None) count
    assert lines[0]["id"] == 1
    assert lines[1]["id"] == 2
    assert lines[2]["error"]["code"] == -32700  # parse error
    payload = json.loads(lines[3]["result"]["content"][0]["text"])
    assert payload["count"] == 1
