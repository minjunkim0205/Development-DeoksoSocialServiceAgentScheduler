from datetime import date

import pandas as pd
import streamlit as st

from core.scheduler import SHIFT_LABELS, summarize_assignments
from core.schedule_view import render_schedule_html
from core.storage import delete_schedule, list_schedule_months, load_schedule, save_schedule


LABEL_TO_SHIFT = {label: shift for shift, label in SHIFT_LABELS.items()}
SHIFT_OPTIONS = list(LABEL_TO_SHIFT.keys())
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


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

st.subheader("근무상황부")
st.markdown(render_schedule_html(schedule), unsafe_allow_html=True)

st.subheader("근무표 편집")
roster = df.pivot_table(index=["agent_id", "agent_name"], columns="day", values="근무", aggfunc="first")
roster = roster.reset_index().rename(columns={"agent_id": "관리번호", "agent_name": "이름"})
day_columns = [column for column in roster.columns if isinstance(column, int)]

edited = st.data_editor(
    roster,
    width="stretch",
    hide_index=True,
    num_rows="fixed",
    column_config={
        "관리번호": st.column_config.TextColumn("관리번호", disabled=True),
        "이름": st.column_config.TextColumn("이름", disabled=True),
        **{
            day: st.column_config.SelectboxColumn(str(day), options=SHIFT_OPTIONS, required=True)
            for day in day_columns
        },
    },
)

if st.button("수정사항 저장", type="primary"):
    updated_by_key = {}
    for _, row in edited.iterrows():
        for day in day_columns:
            updated_by_key[(str(row["관리번호"]), int(day))] = LABEL_TO_SHIFT[str(row[day])]

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
st.subheader("일자별 인원")
daily = df.pivot_table(index=["day", "weekday"], columns="근무", values="agent_id", aggfunc="count", fill_value=0)
for label in SHIFT_OPTIONS:
    if label not in daily.columns:
        daily[label] = 0
daily = daily[SHIFT_OPTIONS].reset_index().rename(columns={"day": "일", "weekday": "요일"})
st.dataframe(daily, width="stretch", hide_index=True)
