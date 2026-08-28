"""Tests for the linter rules, scoring, and formatting."""

from skillkit.linter import ERROR, INFO, lint_skill
from skillkit.model import load_skill

GOOD = """---
name: pdf-tools
description: Extracts text and tables from PDF files, fills forms, and merges PDFs. Use when the user mentions PDFs, forms, or document extraction.
---

## Steps

1. Open the PDF with the parser script in scripts/.
2. Return extracted tables as CSV.

""" + ("Detail line.\n" * 30)


def write(tmp_path, folder, content):
    root = tmp_path / folder
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(content, encoding="utf-8")
    return root


def rules(report):
    return {f.rule for f in report.findings}


def test_clean_skill_passes(tmp_path):
    report = lint_skill(write(tmp_path, "pdf-tools", GOOD))
    assert report.ok
    assert report.score == 100
    assert report.grade == "A"


def test_name_folder_mismatch_is_error(tmp_path):
    report = lint_skill(write(tmp_path, "wrong-folder", GOOD))
    assert "SKILL002" in rules(report)
    assert not report.ok


def test_invalid_name_charset_is_error(tmp_path):
    content = GOOD.replace("name: pdf-tools", "name: PDF Tools")
    report = lint_skill(write(tmp_path, "wrong-folder", content))
    assert "SKILL001" in rules(report)


def test_reserved_name_is_error(tmp_path):
    content = GOOD.replace("name: pdf-tools", "name: claude")
    report = lint_skill(write(tmp_path, "claude", content))
    assert "SKILL001" in rules(report)


def test_overlong_description_is_error(tmp_path):
    content = GOOD.replace(
        "merges PDFs.", "merges PDFs. " + "Extra " * 250
    )  # > 1024 chars
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert "SKILL003" in rules(report)


def test_vague_description_warns(tmp_path):
    content = GOOD.replace(
        "Extracts text and tables from PDF files, fills forms, and merges PDFs. "
        "Use when the user mentions PDFs, forms, or document extraction.",
        "Helps with documents.",
    )
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert "SKILL004" in rules(report)
    assert report.warnings


def test_long_body_warns(tmp_path):
    content = GOOD + ("More detail.\n" * 600)
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert "SKILL005" in rules(report)


def test_thin_body_info(tmp_path):
    content = "---\nname: x\ndescription: Extracts and merges PDF files on demand.\n---\nDo it.\n"
    report = lint_skill(write(tmp_path, "x", content))
    assert "SKILL006" in rules(report)
    severities = {f.severity for f in report.findings}
    assert INFO in severities


def test_github_token_detected_as_error(tmp_path):
    content = GOOD + "\nUse this key: ghp_" + "aB3kX9QwErTyUiOpAsDf" * 2 + "\n"
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    sec = [f for f in report.findings if f.rule == "SEC001"]
    assert sec and sec[0].severity == ERROR


def test_private_key_block_detected(tmp_path):
    content = GOOD + "\n-----BEGIN RSA PRIVATE KEY-----\n"
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert any(f.rule == "SEC001" for f in report.findings)


def test_hardcoded_assignment_detected(tmp_path):
    content = GOOD + '\napi_key = "AKIAIJCKYS3EXAMPLE123"\n'
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert any(f.rule == "SEC001" for f in report.findings)


def test_folder_typo_warns(tmp_path):
    root = write(tmp_path, "pdf-tools", GOOD)
    (root / "script").mkdir()
    report = lint_skill(root)
    assert "SKILL007" in rules(report)


def test_unknown_frontmatter_field_info(tmp_path):
    content = GOOD.replace("license: MIT", "") if "license" in GOOD else GOOD
    content = content.replace(
        "description:", "temperature: 0.7\ndescription:", 1
    )
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert "SKILL008" in rules(report)


def test_metadata_must_be_map(tmp_path):
    content = GOOD.replace("---\n", "---\nmetadata: oops\n", 1)
    report = lint_skill(write(tmp_path, "pdf-tools", content))
    assert "SKILL009" in rules(report)


def test_unloadable_skill_reports_error(tmp_path):
    root = tmp_path / "broken"
    root.mkdir()
    report = lint_skill(root)
    assert not report.ok
    assert report.findings[0].rule == "SKILL000"


def test_score_penalty_and_grades(tmp_path):
    clean = lint_skill(write(tmp_path / "a", "pdf-tools", GOOD))
    assert clean.score == 100

    warned = GOOD.replace(
        "Extracts text and tables from PDF files, fills forms, and merges PDFs. "
        "Use when the user mentions PDFs, forms, or document extraction.",
        "Basic.",
    )
    report = lint_skill(write(tmp_path / "b", "pdf-tools", warned))
    assert report.score == 90
    assert report.grade == "A"


def test_format_report_contains_score(tmp_path):
    from skillkit.linter import format_report

    report = lint_skill(write(tmp_path, "pdf-tools", GOOD))
    text = format_report(report, use_color=False)
    assert "100/100" in text
    assert "grade A" in text


def test_load_skill_still_works_for_borderline_names(tmp_path):
    # loader returns the skill even when the name violates the spec;
    # enforcement belongs to the linter.
    content = "---\nname: Bad_Name\ndescription: Perfectly fine description here.\n---\nbody"
    root = write(tmp_path, "bad", content)
    skill = load_skill(root)
    assert skill.name == "Bad_Name"
