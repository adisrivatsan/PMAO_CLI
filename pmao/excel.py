from pathlib import Path
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter

from pmao.models import Initiative

# ── Column definitions ─────────────────────────────────────────────────────────

INITIATIVE_COLS = [
    "initiative_id",
    "initiative",
    "coordination_owner",
    "responsible_owner",
    "status",
    "priority",
    "current_state",
    "coordination_next_steps",
    "outstanding_questions",
    "outstanding_meetings",
    "last_touch_comment",
    "last_touch_timestamp",
    "syndication_notes",
    "materials_link",
    "notes",
]

NEXT_STEPS_LOG_COLS = ["initiative_id", "initiative", "coordination_next_steps", "date_captured"]

LAST_TOUCH_LOG_COLS = ["initiative_id", "initiative", "last_touch_timestamp", "last_touch_comment"]

MEETING_REQUEST_COLS = [
    "initiative_ids", "initiative", "meeting_title", "duration",
    "suggested_date", "attendees", "scheduler_responsible", "notes", "status",
]

MILESTONE_COLS = [
    "date", "end_date", "title", "type", "priority",
    "initiative_ids", "context", "status",
]

# ── Styles ─────────────────────────────────────────────────────────────────────

_HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_GREEN  = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
_YELLOW = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
_GRAY   = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
_THIN   = Side(style="thin", color="BFBFBF")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _write_header_row(ws, cols: list) -> None:
    for ci, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=ci, value=col_name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = _BORDER
    ws.row_dimensions[1].height = 30


def _write_data_row(ws, row_num: int, cols: list, record: dict) -> None:
    for ci, col_name in enumerate(cols, start=1):
        val = record.get(col_name, "") or ""
        cell = ws.cell(row=row_num, column=ci, value=val)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = _BORDER


def _add_status_cf(ws, status_col_idx: int, max_row: int, num_cols: int) -> None:
    status_letter = get_column_letter(status_col_idx)
    data_range = f"A2:{get_column_letter(num_cols)}{max_row}"
    ws.conditional_formatting.add(data_range, FormulaRule(
        formula=[f'${status_letter}2="ready"'], fill=_GREEN,
    ))
    ws.conditional_formatting.add(data_range, FormulaRule(
        formula=[f'${status_letter}2="in_progress"'], fill=_YELLOW,
    ))
    ws.conditional_formatting.add(data_range, FormulaRule(
        formula=[f'${status_letter}2="complete"'], fill=_GRAY,
    ))


def create_workbook(
    path: Path,
    initiatives: List[Initiative],
    meeting_requests: Optional[list] = None,
    milestones: Optional[list] = None,
) -> None:
    wb = Workbook()

    # ── Tab 1: Initiatives ────────────────────────────────────────────────────
    ws_init = wb.active
    ws_init.title = "Initiatives"
    _write_header_row(ws_init, INITIATIVE_COLS)

    for row_num, init in enumerate(initiatives, start=2):
        record = {
            "initiative_id": init.id,
            "initiative": init.name,
            "coordination_owner": init.coordination_owner or "",
            "responsible_owner": init.responsible_owner or "",
            "status": init.status,
            "priority": init.priority or "",
            "current_state": init.current_state or "",
            "coordination_next_steps": init.coordination_next_steps or "",
            "outstanding_questions": init.outstanding_questions or "",
            "outstanding_meetings": init.outstanding_meetings or "",
            "last_touch_comment": init.last_touch_comment or "",
            "last_touch_timestamp": init.last_touch_timestamp.isoformat() if init.last_touch_timestamp else "",
            "syndication_notes": init.syndication_notes or "",
            "materials_link": init.materials_link or "",
            "notes": init.notes or "",
        }
        _write_data_row(ws_init, row_num, INITIATIVE_COLS, record)

    status_col = INITIATIVE_COLS.index("status") + 1
    _add_status_cf(ws_init, status_col, max(2, 1 + len(initiatives)), len(INITIATIVE_COLS))

    ws_init.column_dimensions["A"].width = 10
    ws_init.column_dimensions["B"].width = 32
    ws_init.column_dimensions["C"].width = 24
    ws_init.column_dimensions["D"].width = 24
    ws_init.column_dimensions["E"].width = 14
    ws_init.column_dimensions["F"].width = 10
    ws_init.column_dimensions["G"].width = 40
    ws_init.column_dimensions["H"].width = 40
    ws_init.column_dimensions["I"].width = 38
    ws_init.column_dimensions["J"].width = 38
    ws_init.column_dimensions["K"].width = 40
    ws_init.column_dimensions["L"].width = 16
    ws_init.column_dimensions["M"].width = 30
    ws_init.column_dimensions["N"].width = 30
    ws_init.column_dimensions["O"].width = 40
    ws_init.freeze_panes = "B2"

    # ── Tab 2: Full Next Steps Log ────────────────────────────────────────────
    ws_log = wb.create_sheet("Full Next Steps Log", index=1)
    _write_header_row(ws_log, NEXT_STEPS_LOG_COLS)
    for row_num, init in enumerate(initiatives, start=2):
        _write_data_row(ws_log, row_num, NEXT_STEPS_LOG_COLS, {
            "initiative_id": init.id,
            "initiative": init.name,
            "coordination_next_steps": init.coordination_next_steps or "",
            "date_captured": init.last_touched.isoformat(),
        })
    ws_log.column_dimensions["A"].width = 12
    ws_log.column_dimensions["B"].width = 32
    ws_log.column_dimensions["C"].width = 80
    ws_log.column_dimensions["D"].width = 14
    ws_log.freeze_panes = "A2"

    # ── Tab 3: Last Touch Log ─────────────────────────────────────────────────
    ws_lt = wb.create_sheet("Last Touch Log", index=2)
    _write_header_row(ws_lt, LAST_TOUCH_LOG_COLS)
    for row_num, init in enumerate(initiatives, start=2):
        _write_data_row(ws_lt, row_num, LAST_TOUCH_LOG_COLS, {
            "initiative_id": init.id,
            "initiative": init.name,
            "last_touch_timestamp": init.last_touch_timestamp.isoformat() if init.last_touch_timestamp else "",
            "last_touch_comment": init.last_touch_comment or "",
        })
    ws_lt.column_dimensions["A"].width = 12
    ws_lt.column_dimensions["B"].width = 32
    ws_lt.column_dimensions["C"].width = 16
    ws_lt.column_dimensions["D"].width = 80
    ws_lt.freeze_panes = "A2"

    # ── Tab 4: Meeting Requests ───────────────────────────────────────────────
    ws_mr = wb.create_sheet("Meeting Requests")
    _write_header_row(ws_mr, MEETING_REQUEST_COLS)
    if meeting_requests:
        for row_num, mr in enumerate(meeting_requests, start=2):
            _write_data_row(ws_mr, row_num, MEETING_REQUEST_COLS, mr)
    ws_mr.freeze_panes = "A2"

    # ── Tab 5: Milestones ─────────────────────────────────────────────────────
    ws_ms = wb.create_sheet("Milestones")
    _write_header_row(ws_ms, MILESTONE_COLS)
    if milestones:
        for row_num, ms in enumerate(milestones, start=2):
            _write_data_row(ws_ms, row_num, MILESTONE_COLS, ms)
    ws_ms.freeze_panes = "A2"

    wb.save(path)
