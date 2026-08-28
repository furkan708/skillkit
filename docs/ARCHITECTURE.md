# skillkit — Architecture

A map of the codebase for contributors and reviewers.

## Module overview

```
skillkit/
├── frontmatter.py   # minimal YAML subset parser (no PyYAML dependency)
├── model.py         # Skill dataclass, loading, discovery
├── linter.py        # rules, secret patterns, scoring, formatting
├── scaffold.py      # new + pack
├── installer.py     # install / list / remove, git source support
├── mcp_server.py    # MCP stdio server (JSON-RPC 2.0)
└── cli.py           # command dispatch
```

Dependency direction:

```
cli → installer → model
    → scaffold  → model
    → linter    → model
    → mcp_server → model, linter
model → frontmatter
```

Everything below `cli` is importable as a library:
`from skillkit import load_skill, lint_skill, find_skills`.

## Key design decisions

**1. Zero dependencies, including YAML.**
The Agent Skills spec only needs flat keys and one nested string map
(`metadata`). `frontmatter.parse_simple_yaml()` implements exactly that
subset (~80 lines) instead of pulling PyYAML. Deliberate trade-off:
unsupported YAML constructs fail loudly (FrontmatterError) rather than
silently mis-parse.

**2. Loading vs. linting are separate.**
`load_skill()` fails only on *structural* problems (no SKILL.md, missing
required fields, unparseable frontmatter). Spec *violations* that still
let us read the file (uppercase name, overlong description) load fine and
are reported by the linter. This separation keeps `find_skills()`
resilient: one broken skill in a directory never hides the healthy ones —
it shows up as a `✗ broken` entry in `list`.

**3. Secrets regexes are conservative.**
Each pattern matches well-known token shapes (`ghp_`, `AKIA`, `xox`,
PEM headers) or long assignments to credential-ish names. We prefer a rare
false negative over regular false positives — a linter that cries wolf
gets disabled, and then it protects no one.

**4. The MCP server is read-only.**
`list_skills` / `read_skill` / `lint_skill` expose discovery and
knowledge. Installation mutates the host (`~/.claude/skills`); that stays
a human CLI decision. If an agent can talk an MCP server into installing
arbitrary code, every skill you have installed becomes an attack path.

**5. Errors are data, not exceptions, at the edges.**
CLI and MCP translate `SkillError` into `--strict` exit codes and
`isError` tool results respectively; only true misuse (bad flags) exits 2.

## The lint score

```
score = max(0, 100 − 25·errors − 10·warnings)
grade = A ≥ 90 · B ≥ 75 · C ≥ 50 · D < 50
```

Penalty weights encode publishing priorities: one leaked secret (an
error) hurts more than five nits; a skill that will never trigger
(SKILL004) is worth exactly one warning — annoying but fixable in a line.

## MCP surface

| Method | Behavior |
| ------ | -------- |
| `initialize` | Echoes protocol version, advertises `tools` |
| `notifications/*` | Ignored |
| `tools/list` | The three tools with JSON Schemas |
| `tools/call` | Dispatch; `SkillError` → `isError: true` result |
| anything else | `-32601` |

## Testing strategy

| Concern | File | Notes |
| ------- | ---- | ----- |
| Frontmatter parsing | `test_frontmatter.py` | Including adversarial lines |
| Loading/discovery | `test_model.py` | Name rules, broken folders skipped |
| Every lint rule | `test_linter.py` | One test per rule ID + scoring |
| Scaffold/pack | `test_scaffold_pack.py` | Layout, zip contents, clean lint of scaffold |
| Install/list/remove | `test_installer.py` | Real git repo clone via local path |
| MCP protocol | `test_mcp_server.py` | Full loop over in-memory streams |
| CLI end-to-end | `test_cli.py` | Exit codes and JSON output |
