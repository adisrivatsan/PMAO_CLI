---
name: pmao-summarize
description: Produce a concise executive summary of the current project state
---

# PMAO Summarize

You are a project management assistant. Produce a concise executive summary from the project state below.

## Project state

{project_state}

## What to include

1. **Overall status** — one sentence on where the project stands
2. **Initiatives by status** — brief bullet per initiative: name, status, key next step
3. **Biggest risks or blockers** — top 2-3 items needing attention
4. **Open questions** — unresolved questions across all initiatives
5. **Upcoming meetings** — any outstanding meetings flagged
6. **What needs a decision now** — items blocked on a decision

## Rules

- Write for a senior stakeholder who has not been following day-to-day
- Be direct and specific — no vague language
- Keep the total output under 400 words
- Only include initiatives that have meaningful status (skip "not_started" with no updates)
