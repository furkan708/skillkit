"""Scaffold new skill folders and package them as zip archives."""

from __future__ import annotations

import zipfile
from pathlib import Path

from .model import SKILL_FILE

SKILL_TEMPLATE = '''---
name: {name}
description: {description}
---

# {title}

## When to use this skill

Use this skill when the user asks to {action_summary}.

## Instructions

1. TODO: write the step-by-step procedure the agent should follow.
2. Keep each step concrete and actionable — state *what to do*, not why.
3. Move long reference material into `references/` and link it from here.

## Examples

**Input:**

```
TODO: show a realistic input
```

**Output:**

```
TODO: show the expected output
```

## Edge cases

- TODO: list common failure modes and how to handle them.
'''

REFERENCE_TEMPLATE = '''# Reference: {title}

Detailed background the agent can load on demand. Keep this out of
{skill_file} so the main instructions stay small and cheap to load.

## Details

- TODO
'''

USAGE_NOTE = """# {name}

A [Agent Skills](https://agentskills.io) compatible skill, scaffolded by skillkit.

```bash
# validate before publishing
skillkit lint {name}
skillkit pack {name}      # produces {name}.zip
```
"""


def new_skill(
    target_dir: str | Path,
    name: str,
    description: str,
) -> Path:
    """Create a new skill folder with a spec-compliant skeleton.

    Returns the path of the created folder. Raises ValueError if the
    target already exists.
    """
    import re

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        raise ValueError(
            "skill name must be lowercase letters, numbers and hyphens only"
        )
    root = Path(target_dir) / name
    if root.exists():
        raise ValueError(f"'{root}' already exists")

    title = name.replace("-", " ").title()
    action = name.replace("-", " ")
    (root / "references").mkdir(parents=True)
    (root / "scripts").mkdir()

    (root / SKILL_FILE).write_text(
        SKILL_TEMPLATE.format(
            name=name,
            description=description,
            title=title,
            action_summary=action,
        ),
        encoding="utf-8",
    )
    (root / "references" / "usage.md").write_text(
        REFERENCE_TEMPLATE.format(title=title, skill_file=SKILL_FILE),
        encoding="utf-8",
    )
    (root / "scripts" / "example.sh").write_text(
        "#!/usr/bin/env bash\n# Deterministic helper the agent may execute.\necho 'TODO'\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(USAGE_NOTE.format(name=name), encoding="utf-8")
    return root


JUNK_NAMES = {".DS_Store", "Thumbs.db", "__pycache__", ".git"}


def pack_skill(path: str | Path, output: str | Path | None = None) -> Path:
    """Zip a skill folder so it can be uploaded to skill-capable platforms.

    The archive contains a single top-level folder named after the skill.
    Returns the path of the created zip file.
    """
    from .model import load_skill

    skill = load_skill(path)  # also validates the folder structure loads
    zip_path = Path(output) if output else Path(f"{skill.path.name}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(skill.path.rglob("*")):
            if file.is_file() and file.name not in JUNK_NAMES:
                if any(part in JUNK_NAMES for part in file.parts):
                    continue
                arcname = Path(skill.path.name) / file.relative_to(skill.path)
                zf.write(file, arcname.as_posix())
    return zip_path
