import json
import tempfile
from datetime import date
from pathlib import Path

from pmao.models import Initiative
from pmao.vault import init_vault, save_initiatives, load_initiatives, load_list


def _vault(tmp, initiative_id="init-001"):
    vault = Path(tmp)
    init_vault(vault)
    save_initiatives(vault, [Initiative(
        id=initiative_id, name="Pricing", status="in_progress",
        created=date(2026, 6, 1), last_touched=date(2026, 6, 1))])
    return vault


def test_promote_each_category_mints_ids_and_maps_fields():
    from pmao.review import promote_extraction
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        today = date.today().isoformat()
        approved = [
            {"category": "facts", "verdict": "approved",
             "item": {"initiative_id": "init-001", "claim": "cost up 9%", "stated_by": "Sarah Klein",
                      "authority": "owner", "confidence": "high", "inferred": False, "source_span": "l12"}},
            {"category": "hypotheses", "verdict": "promoted",
             "item": {"initiative_id": None, "theory": "margins fine", "held_by": "PM", "source_span": "l20"}},
            {"category": "hypotheses", "verdict": "kept",
             "item": {"initiative_id": "init-001", "theory": "bundling wins", "held_by": "PM",
                      "would_confirm": "pilot data", "source_span": "l22"}},
            {"category": "decisions", "verdict": "approved",
             "item": {"initiative_id": "init-001", "decision": "go with v2", "decided_by": "Sarah Klein",
                      "context": "cheaper", "source_span": "l30"}},
            {"category": "open_questions", "verdict": "approved",
             "item": {"initiative_id": "general", "question": "who owns legal?", "source_span": "l33"}},
            {"category": "principal_signals", "verdict": "approved",
             "item": {"initiative_id": "init-001", "principal": "Sarah Klein", "lever": "pricing",
                      "signal": "wants floor", "implication": "raise floor", "source_span": "l40"}},
            {"category": "meetings_to_schedule", "verdict": "approved",
             "item": {"initiative_id": "init-001", "purpose": "align on cost model", "convener": "Sarah Klein",
                      "attendees": ["Finance"], "functions": ["finance"], "target_timing": "next week",
                      "cadence": "one-time", "source_span": "l50"}},
            {"category": "action_items", "verdict": "approved",
             "item": {"initiative_id": "init-001", "description": "build model", "owner": "Dev Patel",
                      "type": "analysis_required", "due": "unspecified", "source_span": "l60"}},
        ]
        minted = promote_extraction(vault, approved, source="sync.vtt")
        assert len(minted) == 8

        facts = load_list(vault, "facts.json")
        assert len(facts) == 2  # fact + promoted hypothesis
        assert facts[0]["id"] == f"fact-{today}-0000"
        assert facts[0]["claim"] == "cost up 9%"
        assert facts[1]["claim"] == "margins fine"
        assert facts[1]["confidence"] == "high"      # human-validated
        assert facts[1]["authority"] == "unknown"

        hyps = load_list(vault, "hypotheses.json")
        assert len(hyps) == 1 and hyps[0]["hypothesis"] == "bundling wins"
        assert hyps[0]["validation_path"] == "pilot data"

        decs = load_list(vault, "decisions.json")
        assert decs[0]["rationale"] == "cheaper" and decs[0]["owner"] == "Sarah Klein"

        qs = load_list(vault, "questions.json")
        assert qs[0]["initiative_id"] == "general"

        sigs = load_list(vault, "signals.json")
        assert sigs[0]["lever"] == "pricing"

        mtgs = load_list(vault, "meetings.json")
        assert mtgs[0]["id"].startswith("mtg-") and mtgs[0]["status"] == "open"
        assert mtgs[0]["cadence"] == "one-time"

        acts = load_list(vault, "actions.json")
        assert acts[0]["type"] == "analysis_required"
        assert acts[0]["due"] == ""                   # unspecified normalized

        # Initiative side-effects: last_touched + derived outstanding_meetings
        init = load_initiatives(vault)[0]
        assert init.last_touched == date.today()
        assert "align on cost model" in init.outstanding_meetings
        assert "(next week)" in init.outstanding_meetings


def test_promote_merge_updates_existing_action_instead_of_creating():
    from pmao.review import promote_extraction
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        (vault / "actions.json").write_text(json.dumps([
            {"id": "act-old-0000", "initiative_id": "init-001", "description": "build model",
             "owner": "Dev Patel", "due": "", "status": "open"}]))
        approved = [{"category": "action_items", "verdict": "merged", "merged_into": "act-old-0000",
                     "item": {"initiative_id": "init-001", "description": "build the cost model v2",
                              "owner": "Dev Patel", "due": "2026-06-20"}}]
        promote_extraction(vault, approved, source="sync.vtt")
        acts = load_list(vault, "actions.json")
        assert len(acts) == 1
        assert "[updated: build the cost model v2]" in acts[0]["description"]
        assert acts[0]["due"] == "2026-06-20"


def test_outstanding_meetings_only_regenerated_when_meetings_promoted():
    from pmao.review import promote_extraction
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        inits = load_initiatives(vault)
        inits[0].outstanding_meetings = "- preexisting free text"
        save_initiatives(vault, inits)
        approved = [{"category": "facts", "verdict": "approved",
                     "item": {"initiative_id": "init-001", "claim": "x", "stated_by": "", "source_span": "l1"}}]
        promote_extraction(vault, approved, source="s.vtt")
        init = load_initiatives(vault)[0]
        assert init.outstanding_meetings == "- preexisting free text"  # untouched
        assert init.last_touched == date.today()


def test_learning_writers_append_and_cap():
    from pmao.review import append_verdict, append_calibration, CALIBRATION_MAX_LINES
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        append_verdict(vault, {"verdict": "approved", "category": "facts", "summary": "x"})
        append_verdict(vault, {"verdict": "rejected", "category": "facts", "summary": "y"})
        lines = (vault / "learning" / "verdicts.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2 and json.loads(lines[1])["verdict"] == "rejected"

        for i in range(CALIBRATION_MAX_LINES + 50):
            append_calibration(vault, f"lesson {i}")
        cal_lines = (vault / "learning" / "calibration.md").read_text().strip().splitlines()
        assert len(cal_lines) == CALIBRATION_MAX_LINES
        assert f"lesson {CALIBRATION_MAX_LINES + 49}" in cal_lines[-1]   # newest kept
        assert not any("lesson 0 " in ln or ln.endswith("lesson 0") for ln in cal_lines)


def _staged_file(vault, extraction, name="2026-06-10-sync.json", status="pending_review"):
    payload = {"status": status, "ingested": "2026-06-10", "source": "sync.vtt",
               "prompt_version": "pmao-deep-v1.1", "extraction": extraction}
    (vault / "staging" / name).write_text(json.dumps(payload))
    return vault / "staging" / name


def _run_with_inputs(monkeypatch, answers, fn, *args):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))
    fn(*args)


def test_run_review_approve_reject_and_hypothesis_verdicts(monkeypatch, capsys):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        staged = _staged_file(vault, {
            "facts": [{"initiative_id": "init-001", "claim": "cost up 9%", "stated_by": "Sarah Klein",
                       "authority": "owner", "confidence": "high", "inferred": False, "source_span": "l1"}],
            "hypotheses": [{"initiative_id": "init-001", "theory": "bundling wins", "held_by": "PM",
                            "would_confirm": "pilot", "source_span": "l2"}],
            "action_items": [{"initiative_id": "init-001", "description": "junk item", "owner": "",
                              "type": "communication", "due": "", "source_span": "l3"}],
            "alias_flags": [{"variants": ["Dev"], "resolved_to": "Dev Patel", "confidence": "high",
                             "needs_review": True}],
            "review_flags": ["near-discard: vague SLA aside"],
        })
        # answers: alias confirm, fact approve, hypothesis keep, action reject, flag accept-drop
        _run_with_inputs(monkeypatch, ["y", "a", "k", "r", ""], run_review, vault)

        assert len(load_list(vault, "facts.json")) == 1
        assert len(load_list(vault, "hypotheses.json")) == 1
        assert load_list(vault, "actions.json") == []          # rejected
        assert json.loads(staged.read_text())["status"] == "reviewed"

        verdicts = [json.loads(l) for l in
                    (vault / "learning" / "verdicts.jsonl").read_text().strip().splitlines()]
        kinds = {v["verdict"] for v in verdicts}
        assert {"alias_confirmed", "approved", "kept", "rejected", "flag_acknowledged"} <= kinds

        cal = (vault / "learning" / "calibration.md").read_text()
        assert 'alias: "Dev" → "Dev Patel" (confirmed)' in cal
        assert "boundary: rejected action_items" in cal


def test_run_review_edit_changes_fields(monkeypatch):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        _staged_file(vault, {
            "action_items": [{"initiative_id": "general", "description": "build model",
                              "owner": "", "type": "analysis_required", "due": "", "source_span": "l1"}],
        })
        # edit: initiative_id -> init-001, owner -> Dev Patel, description kept (empty input)
        _run_with_inputs(monkeypatch, ["e", "init-001", "Dev Patel", ""], run_review, vault)
        acts = load_list(vault, "actions.json")
        assert acts[0]["initiative_id"] == "init-001"
        assert acts[0]["owner"] == "Dev Patel"
        assert acts[0]["description"] == "build model"


def test_run_review_merge_into_reconciliation_candidate(monkeypatch):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        (vault / "actions.json").write_text(json.dumps([
            {"id": "act-old-0000", "initiative_id": "init-001", "description": "build model",
             "owner": "Dev Patel", "due": "", "status": "open"}]))
        _staged_file(vault, {
            "action_items": [{"initiative_id": "init-001", "description": "build model v2",
                              "owner": "Dev Patel", "type": "analysis_required", "due": "",
                              "source_span": "l1",
                              "reconciliation_candidates": [
                                  {"existing": "act-old-0000", "match_confidence": "high"}]}],
        })
        # approve, then merge yes
        _run_with_inputs(monkeypatch, ["a", "y"], run_review, vault)
        acts = load_list(vault, "actions.json")
        assert len(acts) == 1
        assert "[updated: build model v2]" in acts[0]["description"]


def test_run_review_quit_discards_current_file(monkeypatch):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        staged = _staged_file(vault, {
            "facts": [{"initiative_id": "init-001", "claim": "first", "source_span": "l1"},
                      {"initiative_id": "init-001", "claim": "second", "source_span": "l2"}],
        })
        _run_with_inputs(monkeypatch, ["a", "q"], run_review, vault)   # approve one, then quit
        assert load_list(vault, "facts.json") == []                    # nothing promoted
        assert json.loads(staged.read_text())["status"] == "pending_review"


def test_run_review_nothing_pending(capsys):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        run_review(vault)
        assert "Nothing to review." in capsys.readouterr().out


def test_run_review_skips_corrupt_staging_file(monkeypatch, capsys):
    from pmao.review import run_review
    with tempfile.TemporaryDirectory() as tmp:
        vault = _vault(tmp)
        (vault / "staging" / "bad.json").write_text("{not json")
        run_review(vault)
        out = capsys.readouterr().out
        assert "bad.json" in out and "Nothing to review." in out


def test_cli_review_dispatches():
    import sys
    from unittest.mock import patch
    from pmao.cli import main
    with patch("pmao.review.run_review") as mock_review, \
         patch.object(sys, "argv", ["pmao", "review", "v/"]):
        main()
    mock_review.assert_called_once()
