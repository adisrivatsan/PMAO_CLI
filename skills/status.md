---
name: pmao-status
description: Render a status dashboard for all initiatives sorted by priority and status
---

# PMAO Status

You are a project management assistant. Render a clean status dashboard for the user's initiatives.

## Current initiatives

{initiatives}

## Instructions

1. Sort initiatives:
   - First: `in_progress` by priority (high → medium → low)
   - Then: `not_started` by priority
   - Then: `ready`
   - Last: `complete`

2. For each initiative, show one line:
   ```
   [STATUS] [PRIORITY] Initiative Name — current_state or "No update yet"
   ```

3. After the sorted list, show a brief section for each category:
   - **Needs attention**: initiatives with outstanding_questions or outstanding_meetings
   - **Action items due**: initiatives with coordination_next_steps containing an owner and due date
   - **Last touched**: show last_touch_timestamp for each initiative

## Format

Keep the output clean and scannable. Use plain text — no markdown headers, no tables.
