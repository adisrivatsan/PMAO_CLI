import json
import re
from datetime import date
from pathlib import Path
from typing import List

from pmao.models import Initiative
from pmao.vault import load_initiatives, load_list, refresh_workbook
from pmao.roster import load_roster, render_roster

PROMPT_VERSION = "pmao-deep-v1.0"
CALIBRATION_LINE_CAP = 200
RECON_DECISION_CAP = 20

# category -> the key that summarizes one item of that category
ITEM_CATEGORIES = {
    "facts": "claim",
    "hypotheses": "theory",
    "decisions": "decision",
    "open_questions": "question",
    "principal_signals": "signal",
    "meetings_to_schedule": "purpose",
    "action_items": "description",
}


def _build_deep_prompt(
    skill: str,
    initiatives: List[Initiative],
    roster_text: str,
    recon_text: str,
    calibration_text: str,
    source_text: str,
) -> str:
    init_list = "\n".join(
        f"  {i.id}: {i.name} (status: {i.status})" for i in initiatives
    )
    return (
        skill
        .replace("{initiatives}", init_list)
        .replace("{roster}", roster_text)
        .replace("{reconciliation_candidates}", recon_text)
        .replace("{calibration}", calibration_text)
        .replace("{source}", source_text)
    )


def _reconciliation_block(vault_path: Path) -> str:
    """Open actions + the newest RECON_DECISION_CAP decisions, one per line with ids."""
    actions = [a for a in load_list(vault_path, "actions.json") if a.get("status") == "open"]
    decisions = load_list(vault_path, "decisions.json")[-RECON_DECISION_CAP:]
    lines = []
    for a in actions:
        due = a.get("due") or "no due date"
        lines.append(f"{a['id']}: {a['description']} (owner: {a.get('owner', '?')}, due: {due})")
    for d in decisions:
        lines.append(f"{d['id']}: {d['decision']}")
    return "\n".join(lines) if lines else "none"


def _calibration_block(vault_path: Path) -> str:
    """Last CALIBRATION_LINE_CAP lines of learning/calibration.md (newest lessons win)."""
    cal_path = vault_path / "learning" / "calibration.md"
    if not cal_path.exists():
        return "No prior calibration."
    lines = cal_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-CALIBRATION_LINE_CAP:])


def _validate_extraction(extraction: dict, initiatives: List[Initiative]) -> dict:
    """Default missing keys; flag (never drop) unknown initiative ids — recall over precision."""
    for key in ITEM_CATEGORIES:
        extraction.setdefault(key, [])
    extraction.setdefault("alias_flags", [])
    extraction.setdefault("review_flags", [])
    extraction.setdefault("discard_note", "")
    known = {i.id for i in initiatives}
    for category, summary_key in ITEM_CATEGORIES.items():
        for item in extraction[category]:
            iid = item.get("initiative_id")
            if iid is not None and iid != "general" and iid not in known:
                extraction["review_flags"].append(
                    f"unknown initiative_id '{iid}' on {category}: "
                    f"{str(item.get(summary_key, ''))[:80]}"
                )
    return extraction


def _slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    return re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "source"


def _write_staging(vault_path: Path, extraction: dict, source_name: str) -> Path:
    staging_dir = vault_path / "staging"
    staging_dir.mkdir(exist_ok=True)
    base = f"{date.today().isoformat()}-{_slugify(source_name)}"
    target = staging_dir / f"{base}.json"
    suffix = 2
    while target.exists():
        target = staging_dir / f"{base}-{suffix}.json"
        suffix += 1
    target.write_text(json.dumps({
        "status": "pending_review",
        "ingested": date.today().isoformat(),
        "source": source_name,
        "prompt_version": PROMPT_VERSION,
        "extraction": extraction,
    }, indent=2))
    return target
