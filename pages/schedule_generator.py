import streamlit as st
import pandas as pd
from datetime import date

from core.storage import (
    load_agents,
    save_schedule
)

from core.scheduler import generate_schedule

st.title("근무표 생성")

SHIFT_VALUE_TO_LABEL = {
    "D": "주",
    "N": "야",
    "R": "비",
    "O": "휴"
}

WORK_TYPE_VALUE_TO_LABEL = {
    "general": "일반",
    "day_only": "주간전담",
    "night_only": "야간전담"
}

today = date.today()

# ======================
# Generation Options
# ======================

st.header("생성 조건")

col1, col2 = st.columns(2)

with col1:
    year = st.number_input(
        "연도",
        min_value=2020,
        max_value=2100,
        value=today.year,
        step=1
    )

with col2:
    month = st.selectbox(
        "월",
        list(range(1, 13)),
        index=today.month - 1
    )

agents = load_agents()

active_agents = sorted(
    [
        agent for agent in agents
        if agent.get("active") is True
    ],
    key=lambda x: int(x["id"])
)

st.divider()

# ======================
# Active Agent List
# ======================

st.subheader("근무 대상 요원")

if not active_agents:
    st.warning("복무중 요원이 없습니다. 먼저 요원 관리에서 요원을 추가하세요.")
    st.stop()

agent_df = pd.DataFrame(active_agents)

agent_df["work_type_label"] = agent_df["work_type"].map(
    WORK_TYPE_VALUE_TO_LABEL
).fillna("일반")

st.dataframe(
    agent_df[
        [
            "id",
            "name",
            "work_type_label",
            "is_new",
            "notes"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

# ======================
# Generate Schedule
# ======================

st.subheader("근무표 생성")

st.caption("OR-Tools를 사용해서 조건에 맞는 근무표를 생성합니다.")

if st.button("근무표 생성", type="primary"):

    try:
        schedule = generate_schedule(
            int(year),
            int(month),
            active_agents
        )

        save_schedule(
            f"{year}-{month:02}",
            schedule
        )

        st.toast("근무표 생성 완료", icon="✅")

        assignments = schedule["assignments"]

        preview_df = pd.DataFrame(assignments)
        preview_df["shift_label"] = preview_df["shift"].map(SHIFT_VALUE_TO_LABEL)

        agent_order = {
            agent["name"]: int(agent["id"])
            for agent in active_agents
        }

        st.subheader("생성 결과 미리보기")

        roster_df = preview_df.pivot_table(
            index="agent_name",
            columns="day",
            values="shift_label",
            aggfunc="first"
        )

        roster_df = roster_df.reset_index()
        roster_df = roster_df.rename(columns={"agent_name": "이름"})

        summary_df = preview_df.pivot_table(
            index="agent_name",
            columns="shift_label",
            values="date",
            aggfunc="count",
            fill_value=0
        )

        for col in ["주", "야", "비", "휴"]:
            if col not in summary_df.columns:
                summary_df[col] = 0

        summary_df = summary_df[["주", "야", "비", "휴"]]
        summary_df = summary_df.reset_index()
        summary_df = summary_df.rename(columns={"agent_name": "이름"})

        display_df = roster_df.merge(
            summary_df,
            on="이름",
            how="left"
        )

        display_df["sort_order"] = display_df["이름"].map(agent_order)
        display_df = display_df.sort_values("sort_order")
        display_df = display_df.drop(columns=["sort_order"])

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("일자별 근무 인원")

        daily_summary = preview_df.pivot_table(
            index="shift_label",
            columns="day",
            values="agent_id",
            aggfunc="count",
            fill_value=0
        )

        for row in ["주", "야", "비", "휴"]:
            if row not in daily_summary.index:
                daily_summary.loc[row] = 0

        daily_summary = daily_summary.loc[["주", "야", "비", "휴"]]
        daily_summary = daily_summary.reset_index()
        daily_summary = daily_summary.rename(columns={"shift_label": "구분"})

        st.dataframe(
            daily_summary,
            use_container_width=True,
            hide_index=True
        )

    except ValueError as e:
        st.error(str(e))