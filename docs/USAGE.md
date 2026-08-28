# skillkit — Deep Usage Guide

Beyond the quick start: lint rules in detail, install targets, MCP
integration patterns, and troubleshooting.

## Table of contents

1. [The skill lifecycle](#1-the-skill-lifecycle)
2. [Writing descriptions that trigger](#2-writing-descriptions-that-trigger)
3. [Lint rules reference](#3-lint-rules-reference)
4. [Installing into different agents](#4-installing-into-different-agents)
5. [MCP server integration](#5-mcp-server-integration)
6. [CI usage: lint skills in your pipeline](#6-ci-usage-lint-skills-in-your-pipeline)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. The skill lifecycle

```
skillkit new     → scaffold   (spec-correct skeleton)
      │
   edit SKILL.md → write      (what to do + when to use it)
      │
skillkit lint    → validate   (spec + security + quality score)
      │
skillkit pack    → share      (zip for upload platforms)
      │
skillkit install → activate   (~/.claude/skills or your target)
      │
skillkit mcp     → serve      (agents discover + read via MCP)
```

## 2. Writing descriptions that trigger

The `description` frontmatter field is the *only* thing an agent sees at
startup for each installed skill (~100 tokens each). It must answer two
questions in one line: **what does it do** and **when should it fire**.

```
❌  Helps with documents.
❌  A tool for PDFs.
✅  Extracts text and tables from PDF files, fills PDF forms, and merges
    multiple PDFs. Use when working with PDF documents or when the user
    mentions PDFs, forms, or document extraction.
```

Rules of thumb:

- Lead with concrete verbs (extract, write, deploy, migrate).
- End with "Use when …" and list the keywords a user would actually say.
- skillkit warns (SKILL004) when a description is vague — treat that
  warning as "this skill will never trigger".

## 3. Lint rules reference

### Errors (exit code 1)

| Rule | Check |
| ---- | ----- |
| SEC001 | Leaked secrets in SKILL.md: GitHub tokens (`ghp_…`, `github_pat_…`), AWS keys (`AKIA…`), `sk-…` API keys, Slack tokens (`xox…`), PEM private key blocks, and `password/secret/api_key = "…"` assignments |
| SKILL001 | `name` invalid: must be `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars, not a reserved word (`anthropic`, `claude`) |
| SKILL002 | `name` ≠ folder name |
| SKILL003 | `description` > 1,024 characters |
| SKILL009 | `metadata` is not a string→string map |
| SKILL000 | The folder cannot be loaded at all (missing/unclosed frontmatter) |

### Warnings (exit 1 only with `--strict`)

| Rule | Check |
| ---- | ------ |
| SKILL004 | Vague description (won't trigger) |
| SKILL005 | Body > 500 lines (move detail to `references/`) |
| SKILL007 | Folder-name typos: `script/`, `reference/`, `asset/`, `docs/`, `utils/` |

### Info

| Rule | Check |
| ---- | ------ |
| SKILL006 | Very thin body — add steps and examples |
| SKILL008 | Unknown frontmatter field (spec says agents ignore these) |

### Scoring

`score = 100 − 25·errors − 10·warnings` (floor 0). Grades:
A ≥ 90, B ≥ 75, C ≥ 50, D below. Aim for A before publishing.

### Machine-readable output

```bash
skillkit lint ./my-skill --json | jq '.score, .grade'
```

Exit codes are stable for scripting: `0` clean (or warnings without
`--strict`), `1` findings, `2` usage/IO error.

## 4. Installing into different agents

```bash
skillkit install ./my-skill --agent claude    # ~/.claude/skills (default)
skillkit install ./my-skill --agent project   # ./skills (project-local)
skillkit install ./my-skill --dir /any/path   # explicit directory
```

Installing from a git repository (single skill at root **or** multiple
skills in first-level folders — all of them are installed):

```bash
skillkit install https://github.com/someone/awesome-skills
```

Inspect and manage:

```bash
skillkit list                # name · lines · files · description
skillkit list --json         # machine readable
skillkit remove my-skill
```

Broken skills (missing frontmatter etc.) appear in `list` with a `✗ broken`
marker instead of hiding the healthy ones.

## 5. MCP server integration

```json
{
  "mcpServers": {
    "skillkit": { "command": "skillkit", "args": ["mcp"] }
  }
}
```

| Tool | Purpose |
| ---- | ------- |
| `list_skills` | Discover installed skills (name, description, size) |
| `read_skill` | Load one skill's full SKILL.md instructions |
| `lint_skill` | Validate + score a skill |

`skillkit mcp --dir ./project-skills` serves a specific directory instead
of the default agent dir. The server is read-only by design: agents can
discover and read, never modify or install.

Why serve skills over MCP at all? Agents with skill-directory support load
them natively; agents without it (or remote agents) can still access the
same library through MCP — one source of truth, two delivery paths.

## 6. CI usage: lint skills in your pipeline

```yaml
# .github/workflows/skills.yml
name: Skill lint
steps:
  - run: pip install git+https://github.com/furkan708/skillkit.git
  - run: |
      for d in skills/*/; do skillkit lint "$d" --strict; done
```

Pair it with a pre-push git hook for local gating.

## 7. Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `skillkit: command not found` after install | `pip install .` into the same environment your shell uses; check `PATH`. |
| Lint says name/folder mismatch | Folder and `name:` field must be byte-identical. |
| MCP client shows no tools | Wrong `--dir`? Run `skillkit list --dir <same-path>` to verify skills exist. |
| Skill never triggers in the agent | Run `lint --strict`; fix SKILL004 first. |
| Score dropped after adding content | Body over 500 lines — move detail into `references/` and link it. |
