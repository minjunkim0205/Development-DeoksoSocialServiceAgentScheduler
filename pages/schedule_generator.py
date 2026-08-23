from datetime import date

import pandas as pd
import streamlit as st

from core.scheduler import WORK_TYPE_LABELS, generate_schedule
from core.schedule_view import render_schedule_html
from core.storage import load_agents, load_settings, save_schedule


def id_sort_key(agent: dict) -> tuple[int, str]:
    agent_id = str(agent.get("id", ""))
    return (int(agent_id) if agent_id.isdigit() else 999999999, agent_id)


def normalize_agent(agent: dict, index: int) -> dict:
    return {
        "id": str(agent.get("id") or index),
        "name": str(agent.get("name") or agent.get("id") or index),
        "seniority_rank": index,
        "work_type": agent.get("work_type") or "general",
        "pre_service": bool(agent.get("pre_service", False)),
        "boot_camp_completed": not bool(agent.get("pre_service", False)),
        "training_completed": bool(agent.get("training_completed", True)),
        "active": bool(agent.get("active", True)),
        "notes": str(agent.get("notes") or ""),
    }


st.title("근무표 생성")

today = date.today()
settings = load_settings()
agents = load_agents()
active_source_agents = sorted(
    [agent for agent in agents if agent.get("active") is True],
    key=id_sort_key,
)
active_agents = [normalize_agent(agent, index) for index, agent in enumerate(active_source_agents, start=1)]

col1, col2 = st.columns(2)
with col1:
    year = st.number_input("연도", min_value=2020, max_value=2100, value=today.year, step=1)
with col2:
    month = st.selectbox("월", list(range(1, 13)), index=today.month - 1)

st.divider()
st.subheader("대상 요원")

if not active_agents:
    st.warning("복무 중인 요원이 없습니다. 먼저 요원 관리에서 요원을 등록해 주세요.")
    st.stop()

agent_df = pd.DataFrame(active_agents)
agent_df["work_type_label"] = agent_df["work_type"].map(WORK_TYPE_LABELS).fillna("일반")

st.dataframe(
    agent_df[["seniority_rank", "id", "name", "work_type_label", "boot_camp_completed", "training_completed", "notes"]],
    width="stretch",
    hide_index=True,
    column_config={
        "seniority_rank": "숙련 순번",
        "id": "관리번호",
        "name": "이름",
        "work_type_label": "근무 유형",
        "boot_camp_completed": "훈련소 수료",
        "training_completed": "교육 수료",
        "notes": "메모",
    },
)

st.divider()

with st.expander("적용 규칙", expanded=True):
    st.write(
        f"평일 야간은 {settings['weekday_night_target']}명 우선, 불가하면 1명까지 허용합니다. "
        "금/토/일 야간은 반드시 2명입니다."
    )
    st.write("주간은 평일 최대 2명, 금/토/일 최대 3명입니다.")
    st.write(f"숙련 순번 {settings['senior_pair_rank_limit']}번까지는 야간에 서로 붙지 않습니다.")
    st.write("훈련소 미수료 또는 교육 미수료자는 야간에 서로 붙지 않습니다.")

if st.button("근무표 생성", type="primary"):
    try:
        schedule = generate_schedule(int(year), int(month), active_agents, settings)
        save_schedule(schedule["month_key"], schedule)
        st.toast("근무표를 생성하고 저장했습니다.", icon="✅")

        st.subheader("근무상황부")
        st.markdown(render_schedule_html(schedule), unsafe_allow_html=True)
    except ValueError as error:
        st.error(str(error))
