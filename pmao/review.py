import json
from datetime import date
from pathlib import Path
from typing import List, Optional

from pmao.vault import (
    load_initiatives, save_initiatives, load_list,
    refresh_workbook, STAGED_CATEGORIES,
)

CALIBRATION_MAX_LINES = 500


class _Quit(Exception):
    """User quit mid-file — discard this file's verdicts."""


# ── Promotion core ─────────────────────────────────────────────────────────────

def _record_for(category: str, item: dict, source: str, verdict: str):
    """Map a staged item to (canonical filename, id prefix, record dict without id)."""
    today = date.today().isoformat()
    base = {"initiative_id": item.get("initiative_id"), "source": source, "created": today}
    if category == "facts":
        return "facts.json", "fact", dict(base,
            claim=item.get("claim", ""), stated_by=item.get("stated_by", ""),
            authority=item.get("authority", "unknown"), confidence=item.get("confidence", "med"),
            inferred=bool(item.get("inferred", False)), source_span=item.get("source_span", ""))
    if category == "hypotheses" and verdict == "promoted":
        return "facts.json", "fact", dict(base,
            claim=item.get("theory", ""), stated_by=item.get("held_by", ""),
            authority="unknown", confidence="high", inferred=False,
            source_span=item.get("source_span", ""))
    if category == "hypotheses":  # kept
        return "hypotheses.json", "hyp", dict(base,
            hypothesis=item.get("theory", ""), owner=item.get("held_by", ""),
            validation_path=item.get("would_confirm", ""), status="open",
            source_type="[transcript]")
    if category == "decisions":
        return "decisions.json", "dec", dict(base,
            decision=item.get("decision", ""), rationale=item.get("context", ""),
            owner=item.get("decided_by", ""), status="recorded", source_type="[transcript]")
    if category == "open_questions":
        return "questions.json", "q", dict(base,
            question=item.get("question", ""), status="open")
    if category == "principal_signals":
        return "signals.json", "sig", dict(base,
            principal=item.get("principal", ""), lever=item.get("lever", ""),
            signal=item.get("signal", ""), implication=item.get("implication", ""),
            source_span=item.get("source_span", ""))
    if category == "meetings_to_schedule":
        return "meetings.json", "mtg", dict(base,
            purpose=item.get("purpose", ""), convener=item.get("convener"),
            attendees=item.get("attendees") or [], functions=item.get("functions") or [],
            target_timing=item.get("target_timing", ""), cadence=item.get("cadence", ""),
            status="open")
    if category == "action_items":
        due = item.get("due", "")
        return "actions.json", "act", dict(base,
            description=item.get("description", ""), owner=item.get("owner") or "",
            type=item.get("type", ""), due="" if due == "unspecified" else due,
            status="open")
    raise ValueError(f"unknown category: {category}")


def _mint_id(prefix: str, records: list) -> str:
    return f"{prefix}-{date.today().isoformat()}-{len(records):04d}"


def _apply_merge(records: list, entry: dict) -> None:
    """Fold an approved action item into the existing open action it matched."""
    target = next((r for r in records if r.get("id") == entry["merged_into"]), None)
    if target is None:
        return
    new_desc = entry["item"].get("description", "")
    if new_desc:
        target["description"] = f"{target.get('description', '')} [updated: {new_desc}]"
    new_due = entry["item"].get("due", "")
    if new_due and new_due != "unspecified":
        target["due"] = new_due


def promote_extraction(vault_path: Path, approved: List[dict], source: str) -> List[str]:
    """Write all approved items for one staging file. Returns minted ids.

    approved entries: {"category", "item", "verdict", optional "merged_into"}.
    Merges are supported for action_items; other merged categories are skipped
    (the verdict log records the match).
    """
    by_file = {}
    touched, meeting_touched = set(), set()
    minted = []
    for entry in approved:
        iid = entry["item"].get("initiative_id")
        if iid and iid != "general":
            touched.add(iid)
        if entry.get("merged_into"):
            if entry["category"] == "action_items":
                records = by_file.setdefault("actions.json", load_list(vault_path, "actions.json"))
                _apply_merge(records, entry)
            continue
        fname, prefix, rec = _record_for(entry["category"], entry["item"], source, entry["verdict"])
        records = by_file.setdefault(fname, load_list(vault_path, fname))
        rec_id = _mint_id(prefix, records)
        records.append(dict({"id": rec_id}, **rec))
        minted.append(rec_id)
        if fname == "meetings.json" and iid and iid != "general":
            meeting_touched.add(iid)
    for fname, records in by_file.items():
        (vault_path / fname).write_text(json.dumps(records, indent=2))

    if touched:
        initiatives = load_initiatives(vault_path)
        meetings = load_list(vault_path, "meetings.json")
        for init in initiatives:
            if init.id in touched:
                init.last_touched = date.today()
            if init.id in meeting_touched:
                open_mtgs = [m for m in meetings
                             if m.get("initiative_id") == init.id and m.get("status") == "open"]
                init.outstanding_meetings = "\n".join(
                    f"- {m.get('purpose', '')} ({m.get('target_timing') or 'unscheduled'})"
                    for m in open_mtgs)
        save_initiatives(vault_path, initiatives)
    return minted


# ── Learning writers ───────────────────────────────────────────────────────────

def append_verdict(vault_path: Path, record: dict) -> None:
    learning = vault_path / "learning"
    learning.mkdir(exist_ok=True)
    with open(learning / "verdicts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def append_calibration(vault_path: Path, lesson: str) -> None:
    learning = vault_path / "learning"
    learning.mkdir(exist_ok=True)
    cal = learning / "calibration.md"
    lines = cal.read_text(encoding="utf-8").splitlines() if cal.exists() else []
    lines.append(f"- {date.today().isoformat()} {lesson}")
    cal.write_text("\n".join(lines[-CALIBRATION_MAX_LINES:]) + "\n", encoding="utf-8")
