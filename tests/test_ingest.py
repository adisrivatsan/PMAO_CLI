import json
import tempfile
from datetime import date
from pathlib import Path

from pmao.models import Initiative
from pmao.ingest import apply_updates, _append, _build_ingest_prompt
from pmao.vault import init_vault, save_initiatives, load_initiatives


def _make_initiative(id_="init-001", name="Customer Data Platform", status="not_started"):
    return Initiative(
        id=id_, name=name, status=status,
        created=date(2026, 6, 8), last_touched=date(2026, 6, 8)
    )


def test_append_none_existing():
    assert _append(None, "new text") == "new text"


def test_append_empty_existing():
    assert _append("", "new text") == "new text"


def test_append_extends_with_newline():
    assert _append("existing", "new") == "existing\nnew"


def test_append_empty_new_preserves_existing():
    assert _append("existing", "") == "existing"


def test_apply_updates_maps_generic_fields():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        save_initiatives(vault, [_make_initiative()])

        extraction = {
            "initiatives_updated": [{
                "initiative_id": "init-001",
                "current_state": "Analysis complete",
                "coordination_next_steps": "- Alex to schedule review",
                "outstanding_questions": "",
                "outstanding_meetings": "",
                "last_touch_comment": "[email] Alex confirmed done",
                "last_touch_timestamp": "2026-06-08",
                "materials_link": "",
            }],
            "action_items": [{
                "initiative_id": "init-001",
                "description": "Schedule stakeholder review",
                "owner": "Alex Jordan",
                "due": "2026-06-15",
            }],
            "open_questions": [],
        }

        apply_updates(vault, extraction, "meeting-notes.md")

        initiatives = load_initiatives(vault)
        init = initiatives[0]
        assert init.current_state == "Analysis complete"
        assert init.coordination_next_steps == "- Alex to schedule review"
        assert init.status == "in_progress"
        assert init.last_touch_comment == "[email] Alex confirmed done"
        assert init.last_touch_timestamp == date(2026, 6, 8)

        actions = json.loads((vault / "actions.json").read_text())
        assert len(actions) == 1
        assert actions[0]["owner"] == "Alex Jordan"
        assert actions[0]["description"] == "Schedule stakeholder review"


def test_apply_updates_skips_unknown_initiative():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        save_initiatives(vault, [_make_initiative()])

        extraction = {
            "initiatives_updated": [{"initiative_id": "init-999", "current_state": "ignored"}],
            "action_items": [],
            "open_questions": [],
        }
        apply_updates(vault, extraction, "source.md")

        initiatives = load_initiatives(vault)
        assert initiatives[0].current_state is None


def test_apply_updates_appends_existing_next_steps():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        init = _make_initiative(status="in_progress")
        init.coordination_next_steps = "- Existing step"
        save_initiatives(vault, [init])

        extraction = {
            "initiatives_updated": [{
                "initiative_id": "init-001",
                "coordination_next_steps": "- New step added",
                "current_state": "",
                "outstanding_questions": "",
                "outstanding_meetings": "",
                "last_touch_comment": "",
                "last_touch_timestamp": "",
                "materials_link": "",
            }],
            "action_items": [],
            "open_questions": [],
        }
        apply_updates(vault, extraction, "source.md")

        initiatives = load_initiatives(vault)
        assert "- Existing step" in initiatives[0].coordination_next_steps
        assert "- New step added" in initiatives[0].coordination_next_steps


def test_build_ingest_prompt_substitutes_placeholders():
    skill = "## Initiatives\n{initiatives}\n## Source\n{source}"
    initiatives = [_make_initiative()]
    prompt = _build_ingest_prompt(skill, initiatives, "source content here")
    assert "init-001" in prompt
    assert "Customer Data Platform" in prompt
    assert "source content here" in prompt


def test_apply_updates_adds_open_questions():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        init_vault(vault)
        save_initiatives(vault, [_make_initiative()])

        extraction = {
            "initiatives_updated": [],
            "action_items": [],
            "open_questions": [{"initiative_id": "init-001", "question": "What is the budget?"}],
        }
        apply_updates(vault, extraction, "source.md")

        questions = json.loads((vault / "questions.json").read_text())
        assert len(questions) == 1
        assert questions[0]["question"] == "What is the budget?"
