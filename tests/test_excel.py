import tempfile
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from pmao.models import Initiative
from pmao.excel import create_workbook


def _make_initiative(id_="init-001", **kwargs):
    defaults = dict(
        name="Customer Data Platform",
        status="not_started",
        created=date(2026, 6, 8),
        last_touched=date(2026, 6, 8),
    )
    defaults.update(kwargs)
    return Initiative(id=id_, **defaults)


def test_workbook_has_six_tabs():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        assert wb.sheetnames == [
            "Initiatives",
            "Full Next Steps Log",
            "Last Touch Log",
            "Meeting Requests",
            "Milestones",
            "Hypotheses",
        ]


def test_hypotheses_tab_has_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        ws = wb["Hypotheses"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert headers == ["id", "level", "initiative", "hypothesis", "owner", "validation_path", "status", "created", "source"]


def test_hypotheses_tab_project_level_rows_first():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        init = _make_initiative()
        hyps = [
            {
                "id": "hyp-2026-06-09-0001",
                "initiative_id": "init-001",
                "hypothesis": "Initiative-level hypothesis",
                "owner": "",
                "validation_path": "",
                "status": "open",
                "created": "2026-06-09",
                "source": "call.vtt",
            },
            {
                "id": "hyp-2026-06-09-0000",
                "initiative_id": None,
                "hypothesis": "Project-level hypothesis",
                "owner": "",
                "validation_path": "",
                "status": "open",
                "created": "2026-06-09",
                "source": "call.vtt",
            },
        ]
        create_workbook(path, [init], hypotheses=hyps)
        wb = load_workbook(path)
        ws = wb["Hypotheses"]
        # Row 2 should be the project-level hypothesis (initiative_id None)
        level_col = 2  # "level" is column index 2
        assert ws.cell(2, level_col).value == "Project"
        assert ws.cell(3, level_col).value == "Initiative"


def test_hypotheses_tab_populates_level_column():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        init = _make_initiative()
        hyps = [
            {
                "id": "hyp-2026-06-09-0001",
                "initiative_id": "init-001",
                "hypothesis": "Small practices respond better to outcome-based pricing",
                "owner": "Alex Chen",
                "validation_path": "Run A/B test",
                "status": "open",
                "created": "2026-06-09",
                "source": "strategy-call.vtt",
            },
        ]
        create_workbook(path, [init], hypotheses=hyps)
        wb = load_workbook(path)
        ws = wb["Hypotheses"]
        headers = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
        assert ws.cell(2, headers["level"]).value == "Initiative"
        assert ws.cell(2, headers["initiative"]).value == "Customer Data Platform"
        assert ws.cell(2, headers["hypothesis"]).value == "Small practices respond better to outcome-based pricing"
        assert ws.cell(2, headers["owner"]).value == "Alex Chen"
        assert ws.cell(2, headers["status"]).value == "open"


def test_initiatives_tab_generic_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        ws = wb["Initiatives"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert "initiative" in headers
        assert "coordination_owner" in headers
        assert "responsible_owner" in headers
        assert "current_state" in headers
        assert "coordination_next_steps" in headers
        assert "outstanding_questions" in headers
        assert "outstanding_meetings" in headers
        assert "last_touch_comment" in headers
        assert "last_touch_timestamp" in headers
        # No LRP-specific fields
        assert "elt_presenters" not in headers
        assert "syndication_date" not in headers
        assert "agenda_for_strategy_day" not in headers
        assert "may_28_deadline" not in headers


def test_initiatives_tab_populates_from_initiative():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        init = _make_initiative(
            status="in_progress",
            priority="high",
            coordination_owner="Alex Jordan",
            current_state="Analysis complete",
        )
        create_workbook(path, [init])
        wb = load_workbook(path)
        ws = wb["Initiatives"]
        headers = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
        assert ws.cell(2, headers["initiative"]).value == "Customer Data Platform"
        assert ws.cell(2, headers["status"]).value == "in_progress"
        assert ws.cell(2, headers["coordination_owner"]).value == "Alex Jordan"
        assert ws.cell(2, headers["current_state"]).value == "Analysis complete"


def test_full_next_steps_log_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [_make_initiative()])
        wb = load_workbook(path)
        ws = wb["Full Next Steps Log"]
        headers = [ws.cell(1, c).value for c in range(1, 5)]
        assert headers == ["initiative_id", "initiative", "coordination_next_steps", "date_captured"]


def test_full_next_steps_log_populates():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        init = _make_initiative(coordination_next_steps="- Alex to schedule review")
        create_workbook(path, [init])
        wb = load_workbook(path)
        ws = wb["Full Next Steps Log"]
        assert ws.cell(2, 3).value == "- Alex to schedule review"
        assert ws.cell(2, 4).value == "2026-06-08"


def test_last_touch_log_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [_make_initiative()])
        wb = load_workbook(path)
        ws = wb["Last Touch Log"]
        headers = [ws.cell(1, c).value for c in range(1, 5)]
        assert headers == ["initiative_id", "initiative", "last_touch_timestamp", "last_touch_comment"]


def test_last_touch_log_populates():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        init = _make_initiative(
            last_touch_timestamp=date(2026, 6, 7),
            last_touch_comment="[email] Alex confirmed timeline",
        )
        create_workbook(path, [init])
        wb = load_workbook(path)
        ws = wb["Last Touch Log"]
        assert ws.cell(2, 3).value == "2026-06-07"
        assert ws.cell(2, 4).value == "[email] Alex confirmed timeline"


def test_meeting_requests_tab_has_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        ws = wb["Meeting Requests"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert "initiative_ids" in headers
        assert "meeting_title" in headers
        assert "status" in headers


def test_milestones_tab_has_headers():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        ws = wb["Milestones"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert "date" in headers
        assert "title" in headers
        assert "status" in headers


def test_workbook_creates_with_empty_initiatives():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xlsx"
        create_workbook(path, [])
        wb = load_workbook(path)
        ws = wb["Initiatives"]
        # header row only
        assert ws.max_row == 1
