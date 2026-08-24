from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape


SHIFT_SHORT_LABELS = {
    "D": "주",
    "N": "야",
    "R": "비",
    "O": "휴",
    "X": "###",
}

SUMMARY_COLUMNS = [
    ("D", "주"),
    ("N", "야"),
    ("R", "비"),
    ("O", "휴"),
]

BOTTOM_LABELS = {
    "D": "주간",
    "N": "야간",
    "R": "비번",
    "O": "휴일",
}

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def _weekday(year: int, month: int, day: int) -> str:
    return WEEKDAY_LABELS[date(year, month, day).weekday()]


def _day_class(weekday: str, is_off_day: bool) -> str:
    if weekday in ["토", "일"]:
        return "weekend"
    if is_off_day:
        return "holiday"
    return ""


def render_schedule_html(schedule: dict, title: str | None = None) -> str:
    year = int(schedule["year"])
    month = int(schedule["month"])
    assignments = schedule.get("assignments", [])
    if not assignments:
        return "<p>표시할 배정 데이터가 없습니다.</p>"

    days = sorted({int(item["day"]) for item in assignments})
    off_days = {int(day) for day in schedule.get("off_days", [])}
    agent_order: list[tuple[str, str]] = []
    seen_agents = set()
    assignments_by_agent: dict[str, dict[int, str]] = {}

    for item in assignments:
        agent_id = str(item["agent_id"])
        if agent_id not in seen_agents:
            seen_agents.add(agent_id)
            agent_order.append((agent_id, str(item["agent_name"])))
        assignments_by_agent.setdefault(agent_id, {})[int(item["day"])] = str(item["shift"])

    title = title or f"{month}월 사회복무요원 근무상황부(덕소역)"

    header_day_cells = []
    header_weekday_cells = []
    for day in days:
        weekday = _weekday(year, month, day)
        css_class = _day_class(weekday, day in off_days)
        header_day_cells.append(f'<th class="{css_class}">{day}</th>')
        header_weekday_cells.append(f'<th class="{css_class}">{weekday}</th>')

    rows = []
    for agent_id, agent_name in agent_order:
        shifts = assignments_by_agent.get(agent_id, {})
        counts = Counter(shifts.values())
        shift_cells = []
        for day in days:
            shift = shifts.get(day, "")
            label = SHIFT_SHORT_LABELS.get(shift, "")
            shift_class = "shift-off" if shift == "O" else "shift-inactive" if shift == "X" else ""
            shift_cells.append(f'<td class="{shift_class}">{escape(label)}</td>')

        summary_cells = [f"<td>{counts.get(shift, 0)}</td>" for shift, _ in SUMMARY_COLUMNS]
        rows.append(
            "<tr>"
            f'<th class="name-cell">{escape(agent_name)}</th>'
            + "".join(shift_cells)
            + '<td class="spacer"></td>'
            + "".join(summary_cells)
            + "</tr>"
        )

    daily_counts: dict[str, Counter] = {shift: Counter() for shift, _ in SUMMARY_COLUMNS}
    for item in assignments:
        shift = str(item["shift"])
        if shift in daily_counts:
            daily_counts[shift][int(item["day"])] += 1

    bottom_rows = []
    for shift, _ in SUMMARY_COLUMNS:
        cells = []
        for day in days:
            weekday = _weekday(year, month, day)
            css_class = _day_class(weekday, day in off_days)
            cells.append(f'<td class="{css_class}">{daily_counts[shift].get(day, 0)}</td>')
        bottom_rows.append(
            "<tr>"
            f'<th class="bottom-label">{BOTTOM_LABELS[shift]}</th>'
            + "".join(cells)
            + '<td class="spacer"></td>'
            + "<td></td><td></td><td></td><td></td>"
            + "</tr>"
        )

    summary_header = "".join(f"<th>{label}</th>" for _, label in SUMMARY_COLUMNS)
    empty_bottom_cells = "".join("<td></td>" for _ in days)

    return f"""
<style>
.schedule-wrap {{
  width: 100%;
  overflow-x: auto;
  padding: 8px 0 14px;
}}
.schedule-sheet {{
  border-collapse: collapse;
  table-layout: fixed;
  min-width: 1280px;
  border: 3px solid #2f4774;
  background: #f7f7f7;
  color: #222;
  font-family: Arial, "Malgun Gothic", sans-serif;
  font-size: 17px;
}}
.schedule-sheet th,
.schedule-sheet td {{
  border: 1.5px solid #3f3f3f;
  width: 38px;
  height: 34px;
  text-align: center;
  vertical-align: middle;
  padding: 0;
  font-weight: 600;
}}
.schedule-sheet .title {{
  height: 44px;
  font-size: 28px;
  font-weight: 700;
  background: #f0f0f0;
}}
.schedule-sheet .corner {{
  width: 108px;
  min-width: 108px;
  background: linear-gradient(32deg, transparent 49%, #3f3f3f 50%, transparent 51%);
  position: relative;
}}
.schedule-sheet .corner .date-label {{
  position: absolute;
  right: 12px;
  top: 8px;
  font-size: 14px;
}}
.schedule-sheet .corner .name-label {{
  position: absolute;
  left: 10px;
  bottom: 8px;
  font-size: 14px;
}}
.schedule-sheet .name-cell {{
  width: 108px;
  min-width: 108px;
  font-size: 21px;
  background: #f5f5f5;
}}
.schedule-sheet .spacer {{
  width: 12px;
  min-width: 12px;
  border-top: none;
  border-bottom: none;
  background: #f7f7f7;
}}
.schedule-sheet .weekend {{
  background: #b8d2e9;
}}
.schedule-sheet .holiday {{
  background: #e9b8b8;
}}
.schedule-sheet td.shift-off {{
  background: #d9d9d9;
}}
.schedule-sheet td.shift-inactive {{
  background: #f2f2f2;
  color: #555;
  font-size: 14px;
}}
.schedule-sheet .bottom-gap td,
.schedule-sheet .bottom-gap th {{
  height: 14px;
  border-left: none;
  border-right: none;
  background: #f7f7f7;
}}
</style>
<div class="schedule-wrap">
  <table class="schedule-sheet">
    <tr>
      <th class="title" colspan="{len(days) + 6}">{escape(title)}</th>
    </tr>
    <tr>
      <th class="corner" rowspan="2"><span class="date-label">일자</span><span class="name-label">이름</span></th>
      {''.join(header_day_cells)}
      <td class="spacer" rowspan="2"></td>
      {summary_header}
    </tr>
    <tr>
      {''.join(header_weekday_cells)}
      {summary_header}
    </tr>
    {''.join(rows)}
    <tr class="bottom-gap"><th></th>{empty_bottom_cells}<td class="spacer"></td><td></td><td></td><td></td><td></td></tr>
    {''.join(bottom_rows)}
  </table>
</div>
"""
