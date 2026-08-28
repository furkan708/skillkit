"""Tests for the frontmatter parser."""

import pytest

from skillkit.frontmatter import (
    FrontmatterError,
    parse_simple_yaml,
    parse_skill_document,
    split_frontmatter,
)

DOC = """---
name: pdf-tools
description: Extract text from PDFs. Use when the user mentions PDFs.
license: MIT
metadata:
  author: Furkan
  version: "1.0"
---

# PDF Tools

Step-by-step instructions here.
"""


def test_split_basic_document():
    yaml_text, body = split_frontmatter(DOC)
    assert "name: pdf-tools" in yaml_text
    assert body.lstrip().startswith("# PDF Tools")


def test_split_requires_opening_delimiter():
    with pytest.raises(FrontmatterError):
        split_frontmatter("name: x\n")


def test_split_requires_closing_delimiter():
    with pytest.raises(FrontmatterError):
        split_frontmatter("---\nname: x\n")


def test_parse_flat_keys():
    data = parse_simple_yaml("name: pdf-tools\ndescription: Does things\nlicense: MIT\n")
    assert data == {
        "name": "pdf-tools",
        "description": "Does things",
        "license": "MIT",
    }


def test_parse_nested_metadata_map():
    data = parse_simple_yaml(
        'metadata:\n  author: Furkan\n  version: "1.0"\nname: x\n'
    )
    assert data["metadata"] == {"author": "Furkan", "version": "1.0"}
    assert data["name"] == "x"


def test_quoted_values_are_unquoted():
    assert parse_simple_yaml('name: "my-skill"\n')["name"] == "my-skill"
    assert parse_simple_yaml("name: 'my-skill'\n")["name"] == "my-skill"


def test_comments_and_blank_lines_ignored():
    data = parse_simple_yaml("# header\n\nname: x  # trailing not required\n")
    assert data == {"name": "x"}


def test_value_containing_colon_is_kept():
    data = parse_simple_yaml("description: uses http://example.com API\n")
    assert data["description"] == "uses http://example.com API"


def test_bad_line_raises():
    with pytest.raises(FrontmatterError):
        parse_simple_yaml("just some text without colon\n")


def test_unexpected_indent_raises():
    with pytest.raises(FrontmatterError):
        parse_simple_yaml("name: x\n  orphan: y\n")


def test_parse_skill_document_roundtrip():
    data, body = parse_skill_document(DOC)
    assert data["name"] == "pdf-tools"
    assert data["metadata"]["author"] == "Furkan"
    assert body.lstrip().startswith("# PDF Tools")
