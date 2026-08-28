"""Minimal YAML frontmatter parser for SKILL.md files.

Supports the subset of YAML the Agent Skills specification needs:
top-level ``key: value`` pairs, quoted strings, comments, and one
level of nested string-to-string maps (e.g. ``metadata``).
"""

from __future__ import annotations


class FrontmatterError(ValueError):
    """Raised when the frontmatter block is malformed."""


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a SKILL.md document into (frontmatter_yaml, markdown_body).

    Raises:
        FrontmatterError: If the document does not start with a
            well-formed ``---`` delimited block.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("document must start with a '---' frontmatter delimiter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    raise FrontmatterError("frontmatter block is never closed (missing second '---')")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _strip_comment(value: str) -> str:
    """Remove a trailing ' # comment' from an unquoted value."""
    if len(value) >= 2 and value[0] in ("'", '"'):
        return value  # quoted values keep everything
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def parse_simple_yaml(yaml_text: str) -> dict:
    """Parse the flat/nested-once YAML subset used by skill frontmatter.

    Raises:
        FrontmatterError: On lines that cannot be understood.
    """
    result: dict = {}
    current_map: dict | None = None

    for raw_line in yaml_text.replace("\r\n", "\n").split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise FrontmatterError(f"cannot parse frontmatter line: {raw_line!r}")

        indent = len(line) - len(line.lstrip(" "))
        key_part, _, value_part = stripped.partition(":")
        key = key_part.strip()
        value = value_part.strip()

        if indent == 0:
            if value == "" or value in ("{}", "[]"):
                # Value may be a nested map (or deliberately empty).
                current_map = {} if value == "" else None
                result[key] = current_map if current_map is not None else ""
            else:
                result[key] = _unquote(_strip_comment(value))
                current_map = None
        else:
            if current_map is None:
                raise FrontmatterError(f"unexpected indented line: {raw_line!r}")
            if not value:
                raise FrontmatterError(f"nested map values must be inline: {raw_line!r}")
            current_map[key] = _unquote(_strip_comment(value))

    # An empty nested map should stay a dict, not None.
    for key, value in list(result.items()):
        if value is None:
            result[key] = {}
    return result


def parse_skill_document(text: str) -> tuple[dict, str]:
    """Parse a full SKILL.md document into (frontmatter_dict, body)."""
    yaml_text, body = split_frontmatter(text)
    return parse_simple_yaml(yaml_text), body
