from datetime import date

import pandas as pd
import streamlit as st

from core.scheduler import SHIFT_LABELS, summarize_assignments
from core.schedule_view import render_schedule_html
from core.storage import delete_schedule, list_schedule_months, load_schedule, save_schedule


LABEL_TO_SHIFT = {label: shift for shift, label in SHIFT_LABELS.items()}
SHIFT_OPTIONS = list(LABEL_TO_SHIFT.keys())
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
SUMMARY_LABELS = ["주간", "야간", "비번", "휴일"]


st.title("근무표 수정")

months = list_schedule_months()
if not months:
    st.info("저장된 근무표가 없습니다.")
    st.stop()

month_key = st.selectbox("월 선택", months)

with st.expander("근무표 삭제"):
    delete_year, delete_month = month_key.split("-")
    delete_phrase = f"{int(delete_year)}년 {int(delete_month)}월 근무표 삭제"
    st.warning("정말 삭제하시겠습니까? 삭제 후에는 복구할 수 없습니다.")
    st.caption(f'삭제하시려면 "{delete_phrase}" 를 입력해 주십시오.')
    confirm_delete = st.text_input("삭제 확인 문구")
    if st.button("선택한 근무표 삭제", disabled=confirm_delete != delete_phrase):
        if delete_schedule(month_key):
            st.toast(f"{month_key} 근무표를 삭제했습니다.", icon="✅")
            st.rerun()
        else:
            st.error("삭제할 근무표 파일을 찾지 못했습니다.")

schedule = load_schedule(month_key)
if not schedule:
    st.error("근무표 파일을 읽을 수 없습니다.")
    st.stop()

assignments = schedule.get("assignments", [])
if not assignments:
    st.warning("배정 데이터가 비어 있습니다.")
    st.stop()

df = pd.DataFrame(assignments)
if "weekday" not in df.columns:
    year = int(schedule["year"])
    month = int(schedule["month"])
    df["weekday"] = df["day"].apply(lambda day: WEEKDAY_LABELS[date(year, month, int(day)).weekday()])

df["근무"] = df["shift"].map(SHIFT_LABELS)

st.subheader("근무상황부 편집")
roster = df.pivot_table(index=["agent_id", "agent_name"], columns="day", values="근무", aggfunc="first")
roster = roster.reset_index().rename(columns={"agent_id": "관리번호", "agent_name": "이름"})
day_numbers = [column for column in roster.columns if isinstance(column, int)]
day_labels = {
    day: f"{day}\n{WEEKDAY_LABELS[date(int(schedule['year']), int(schedule['month']), int(day)).weekday()]}"
    for day in day_numbers
}
day_by_label = {label: day for day, label in day_labels.items()}
roster = roster.rename(columns=day_labels)

for label, shift in [("주", "D"), ("야", "N"), ("비", "R"), ("휴", "O")]:
    roster[label] = roster[list(day_by_label)].eq(SHIFT_LABELS[shift]).sum(axis=1)

edited = st.data_editor(
    roster,
    width="stretch",
    hide_index=True,
    num_rows="fixed",
    column_order=["관리번호", "이름", *day_by_label.keys(), "주", "야", "비", "휴"],
    column_config={
        "관리번호": st.column_config.TextColumn("관리번호", disabled=True),
        "이름": st.column_config.TextColumn("이름", disabled=True),
        **{
            day_label: st.column_config.SelectboxColumn(day_label, options=SHIFT_OPTIONS, required=True)
            for day_label in day_by_label
        },
        "주": st.column_config.NumberColumn("주", disabled=True),
        "야": st.column_config.NumberColumn("야", disabled=True),
        "비": st.column_config.NumberColumn("비", disabled=True),
        "휴": st.column_config.NumberColumn("휴", disabled=True),
    },
    key=f"schedule_editor_{month_key}",
)

st.subheader("일자별 인원")
daily_rows = []
for label, shift in zip(SUMMARY_LABELS, ["D", "N", "R", "O"]):
    row = {"구분": label}
    for day_label in day_by_label:
        row[day_label] = int(edited[day_label].eq(SHIFT_LABELS[shift]).sum())
    daily_rows.append(row)
st.dataframe(pd.DataFrame(daily_rows), width="stretch", hide_index=True)

if st.button("수정사항 저장", type="primary"):
    updated_by_key = {}
    for _, row in edited.iterrows():
        for day_label, day in day_by_label.items():
            updated_by_key[(str(row["관리번호"]), int(day))] = LABEL_TO_SHIFT[str(row[day_label])]

    updated_assignments = []
    for assignment in assignments:
        key = (str(assignment["agent_id"]), int(assignment["day"]))
        updated_assignments.append({**assignment, "shift": updated_by_key[key]})

    updated_schedule = {
        **schedule,
        "summary": summarize_assignments(updated_assignments),
        "assignments": updated_assignments,
    }
    save_schedule(month_key, updated_schedule)
    st.toast("근무표를 저장했습니다.", icon="✅")
    st.rerun()

st.divider()
st.subheader("HTML 근무상황부")
st.markdown(render_schedule_html(schedule), unsafe_allow_html=True)
