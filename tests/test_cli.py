"""End-to-end CLI tests."""

import json

import pytest

from skillkit.cli import main


@pytest.fixture()
def skill(tmp_path):
    from skillkit.scaffold import new_skill

    return new_skill(
        tmp_path,
        "cli-skill",
        "Exercises the command-line interface end to end. Use in CLI tests.",
    )


def test_new_and_lint_clean(tmp_path, capsys):
    main(["new", "fresh", "-d", "Creates fresh skill folders for teams.", "--dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "created" in out

    code = 0
    try:
        main(["lint", str(tmp_path / "fresh")])
    except SystemExit as e:
        code = e.code
    assert code in (None, 0)


def test_lint_json_output(skill, capsys):
    main(["lint", str(skill), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["skill"] == "cli-skill"
    assert payload["grade"] == "A"


def test_lint_error_exits_1(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()  # no SKILL.md
    with pytest.raises(SystemExit) as exc:
        main(["lint", str(broken)])
    assert exc.value.code == 1


def test_lint_strict_warns_exits_1(tmp_path):
    from skillkit.scaffold import new_skill

    vague = new_skill(tmp_path, "vague", "Helps with stuff.")
    with pytest.raises(SystemExit) as exc:
        main(["lint", str(vague), "--strict"])
    assert exc.value.code == 1


def test_pack_command(skill, tmp_path, capsys):
    main(["pack", str(skill), "-o", str(tmp_path / "out.zip")])
    assert "packed" in capsys.readouterr().out
    assert (tmp_path / "out.zip").is_file()


def test_install_and_list_and_remove(skill, tmp_path, capsys):
    target = tmp_path / "skills"
    main(["install", str(skill), "--dir", str(target)])
    assert "installed" in capsys.readouterr().out

    main(["list", "--dir", str(target)])
    out = capsys.readouterr().out
    assert "cli-skill" in out

    main(["list", "--dir", str(target), "--json"])
    entries = json.loads(capsys.readouterr().out)
    assert entries[0]["name"] == "cli-skill"

    main(["remove", "cli-skill", "--dir", str(target)])
    assert "removed" in capsys.readouterr().out
    assert not (target / "cli-skill").exists()


def test_list_empty_directory(tmp_path, capsys):
    main(["list", "--dir", str(tmp_path / "nothing")])
    out = capsys.readouterr().out
    assert "no skills installed" in out


def test_install_invalid_skill_fails(tmp_path, capsys):
    broken = tmp_path / "broken"
    broken.mkdir()
    with pytest.raises(SystemExit) as exc:
        main(["install", str(broken), "--dir", str(tmp_path / "x")])
    assert exc.value.code == 2


def test_mcp_command_serves_one_request(skill, tmp_path, capsys, monkeypatch):
    import io

    from skillkit.cli import USE_COLOR  # noqa: F401  (ensure import path works)

    requests = io.BytesIO(
        (
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        ).encode()
    )
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(requests, encoding="utf-8"))
    main(["mcp", "--dir", str(tmp_path)])
    out = capsys.readouterr().out
    response = json.loads(out.splitlines()[0])
    assert response["result"]["serverInfo"]["name"] == "skillkit"
