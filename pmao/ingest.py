import json
from datetime import date
from pathlib import Path
from typing import List, Optional

from pmao.models import Initiative
from pmao.vault import load_initiatives, save_initiatives
from pmao.excel import create_workbook


def _load_skill(skill_name: str) -> str:
    skills_dir = Path(__file__).parent.parent / "skills"
    skill_file = skills_dir / f"{skill_name}.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_file}")
    return skill_file.read_text(encoding="utf-8")


def _build_ingest_prompt(skill: str, initiatives: List[Initiative], source_text: str) -> str:
    init_list = "\n".join(
        f"  {i.id}: {i.name} (status: {i.status})"
        for i in initiatives
    )
    return skill.replace("{initiatives}", init_list).replace("{source}", source_text)


def _append(existing: Optional[str], new_text: str) -> str:
    if not new_text:
        return existing or ""
    if not existing:
        return new_text
    return f"{existing}\n{new_text}"


def apply_updates(vault_path: Path, extraction: dict, transcript_name: str) -> None:
    initiatives = load_initiatives(vault_path)
    idx = {i.id: i for i in initiatives}
    today = date.today()

    for update in extraction.get("initiatives_updated", []):
        iid = update.get("initiative_id")
        if iid not in idx:
            continue
        init = idx[iid]
        init.current_state = _append(init.current_state, update.get("current_state", ""))
        init.coordination_next_steps = _append(init.coordination_next_steps, update.get("coordination_next_steps", ""))
        init.outstanding_questions = _append(init.outstanding_questions, update.get("outstanding_questions", ""))
        init.outstanding_meetings = _append(init.outstanding_meetings, update.get("outstanding_meetings", ""))
        init.last_touch_comment = _append(init.last_touch_comment, update.get("last_touch_comment", ""))
        ts = update.get("last_touch_timestamp", "")
        if ts:
            try:
                init.last_touch_timestamp = date.fromisoformat(ts)
            except ValueError:
                pass
        if update.get("materials_link"):
            init.materials_link = update["materials_link"]
        if init.status == "not_started":
            init.status = "in_progress"
        init.last_touched = today

    actions_path = vault_path / "actions.json"
    actions = json.loads(actions_path.read_text()) if actions_path.exists() else []
    for item in extraction.get("action_items", []):
        if not item.get("description") or not item.get("owner"):
            continue
        actions.append({
            "id": f"act-{today.isoformat()}-{len(actions):04d}",
            "initiative_id": item.get("initiative_id", ""),
            "description": item["description"],
            "owner": item["owner"],
            "due": item.get("due", ""),
            "status": "open",
            "created": today.isoformat(),
            "source": transcript_name,
        })
    actions_path.write_text(json.dumps(actions, indent=2))

    questions_path = vault_path / "questions.json"
    questions = json.loads(questions_path.read_text()) if questions_path.exists() else []
    for q in extraction.get("open_questions", []):
        if not q.get("question"):
            continue
        questions.append({
            "id": f"q-{today.isoformat()}-{len(questions):04d}",
            "initiative_id": q.get("initiative_id", ""),
            "question": q["question"],
            "status": "open",
            "created": today.isoformat(),
            "source": transcript_name,
        })
    questions_path.write_text(json.dumps(questions, indent=2))

    save_initiatives(vault_path, initiatives)
    create_workbook(vault_path / "workbook.xlsx", initiatives)


def run_ingest(
    vault_path: Path,
    source_path: Path,
    yes: bool = False,
    config_override: str = None,
) -> None:
    from pmao.transcript import preprocess_transcript
    from pmao.llm import call_structured

    print(f"Preprocessing {source_path.name}...")
    text = preprocess_transcript(source_path)

    initiatives = load_initiatives(vault_path)
    skill = _load_skill("ingest")
    prompt = _build_ingest_prompt(skill, initiatives, text)

    print("Calling LLM for extraction (this may take ~30s)...")
    extraction = call_structured(prompt, config_override=config_override)
    extraction.setdefault("initiatives_updated", [])
    extraction.setdefault("action_items", [])
    extraction.setdefault("open_questions", [])

    init_updates = extraction["initiatives_updated"]
    action_items = extraction["action_items"]
    questions = extraction["open_questions"]

    print(f"\n--- Extraction results ---")
    print(f"Initiatives updated: {len(init_updates)}")
    for u in init_updates:
        iid = u.get("initiative_id", "?")
        name = next((i.name for i in initiatives if i.id == iid), iid)
        print(f"  [{iid}] {name}")
    print(f"Action items: {len(action_items)}")
    print(f"Open questions: {len(questions)}")

    if not init_updates and not action_items and not questions:
        print("\nNothing extracted — no changes made.")
        return

    if not yes:
        answer = input("\nApply these updates? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    apply_updates(vault_path, extraction, transcript_name=source_path.name)
    print(f"\nDone. workbook.xlsx updated.")
