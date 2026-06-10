from pathlib import Path

SKILL_PATH = Path(__file__).parent.parent / "skills" / "ingest-deep.md"
PLACEHOLDERS = ["{initiatives}", "{roster}", "{reconciliation_candidates}", "{calibration}", "{source}"]


def test_skill_file_has_all_placeholders():
    text = SKILL_PATH.read_text(encoding="utf-8")
    for ph in PLACEHOLDERS:
        assert ph in text, f"missing placeholder {ph}"


def test_skill_file_has_no_legacy_roster_or_chunking():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "owner_roster" not in text
    assert "principal_roster" not in text
    assert "pre-chunked" not in text
    assert '"chunk": "1/1"' in text
    assert "pmao-deep-v1.0" in text


def test_skill_file_requires_initiative_id_everywhere():
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Every category block in the output schema carries initiative_id
    assert text.count('"initiative_id"') >= 7
