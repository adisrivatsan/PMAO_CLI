# pmao-cli

**Project Management Assistant Orchestrator** — a CLI-first, LLM-powered initiative tracker.

pmao maintains a local "vault" of JSON files as source of truth and uses an LLM (Claude Code or OpenAI Codex CLI) to extract updates from meeting notes, generate status dashboards, and produce executive summaries. All reasoning lives in plain-text skill files you can read and edit.

## Requirements

- Python 3.9+
- [Claude Code CLI](https://github.com/anthropics/claude-code) (`claude`) **or** [OpenAI Codex CLI](https://github.com/openai/codex) (`codex`) on your PATH
- `pip install pmao-cli`

## Quick start

```bash
# 1. Create a vault
pmao init my-project/

# 2. Seed initiatives from a CSV (optional)
pmao init my-project/ --roster templates/initiative-template.csv

# 3. Ingest meeting notes or a transcript
pmao ingest my-project/ --source meeting-notes.md

# 4. View a status dashboard
pmao status my-project/

# 5. Produce an executive summary
pmao summarize my-project/

# 6. Regenerate the Excel workbook
pmao export my-project/
```

## Commands

| Command | Description |
|---------|-------------|
| `pmao init <vault> [--roster FILE]` | Initialize a new vault; optionally seed from CSV |
| `pmao ingest <vault> --source FILE [--yes]` | Extract updates from a .vtt, .txt, or .md source |
| `pmao update <vault>` | Interactively update an initiative field via LLM |
| `pmao status <vault>` | Print a sorted status dashboard |
| `pmao summarize <vault>` | Produce an executive summary |
| `pmao export <vault>` | Regenerate workbook.xlsx from current state |
| `pmao config <vault>` | View project configuration |

All LLM commands accept `--backend claude` or `--backend codex` to override auto-detection.

## Vault structure

```
my-project/
  project-config.yaml   # project name, owner, LLM settings
  initiatives.json      # source of truth — all initiative state
  actions.json          # open action items
  questions.json        # open questions
  decisions.json        # recorded decisions
  workbook.xlsx         # derived Excel artifact (5 tabs)
  transcripts/          # drop .vtt or .txt files here
```

## Initiative fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique identifier (e.g., `init-001`) |
| `name` | yes | Initiative name |
| `status` | yes | `not_started` / `in_progress` / `ready` / `complete` |
| `created` | yes | ISO date |
| `last_touched` | yes | ISO date (auto-updated on ingest) |
| `coordination_owner` | no | Person driving coordination |
| `responsible_owner` | no | Person accountable for delivery |
| `priority` | no | `high` / `medium` / `low` |
| `current_state` | no | Free-text state summary |
| `coordination_next_steps` | no | Newline-delimited next steps |
| `outstanding_questions` | no | Unresolved questions |
| `outstanding_meetings` | no | Meetings to schedule |
| `last_touch_comment` | no | Source of last update |
| `last_touch_timestamp` | no | ISO date of last update |
| `syndication_notes` | no | Notes on external communication |
| `materials_link` | no | URL to supporting materials |
| `notes` | no | Freeform notes |

## Skill files

All LLM reasoning is in `skills/`. Edit these to change how the LLM interprets your transcripts or formats its output — no Python changes required.

| File | Used by |
|------|---------|
| `skills/ingest.md` | `pmao ingest` — structured extraction from source material |
| `skills/update.md` | `pmao update` — interactive field update flow |
| `skills/status.md` | `pmao status` — status dashboard rendering |
| `skills/summarize.md` | `pmao summarize` — executive summary generation |

## Seeding initiatives from CSV

Use `--roster` with `pmao init`, or provide a CSV with headers:

```
id,name,coordination_owner,responsible_owner,priority
init-001,Customer Data Platform,Jane Smith,John Doe,high
init-002,Market Expansion,,,medium
```

See `templates/initiative-template.csv` for the full template.

## LLM backend

pmao auto-detects the backend from PATH. To use a specific backend:

```bash
pmao status my-project/ --backend claude
pmao ingest my-project/ --source notes.md --backend codex
```

Or set it permanently in `project-config.yaml`:

```yaml
llm_backend: claude
```

## Examples

See `examples/` for:
- `example-project-config.yaml` — a filled-out config
- `example-source-notes.md` — meeting notes ready to ingest
- `example-output-summary.md` — representative `pmao summarize` output
