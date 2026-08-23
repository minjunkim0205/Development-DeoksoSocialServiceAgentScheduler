import streamlit as st

from core.storage import list_schedule_months, load_agents, load_schedule


st.title("덕소 사회복무요원 근무표")

agents = load_agents()
active_agents = [agent for agent in agents if agent.get("active") is True]
months = list_schedule_months()

col1, col2, col3 = st.columns(3)
col1.metric("전체 요원", len(agents))
col2.metric("복무 중", len(active_agents))
col3.metric("저장된 근무표", len(months))

st.divider()

st.subheader("현재 반영된 기본 규칙")
st.markdown(
    """
- 금/토/일 야간은 반드시 2명 배치
- 평일 야간은 2명을 우선하되, 불가하면 1명 허용
- 주간은 기본 2명, 금/토/일은 최대 3명까지 허용
- 야간 다음날은 비번 강제, 비번 다음날은 휴무 우선
- 주야비휴 흐름을 우선하고, 근무 횟수와 야간 횟수를 최대한 균등하게 배분
- 고참끼리 야간 동시 배치 금지
- 훈련소 미수료 또는 요원교육 미수료자끼리 야간 동시 배치 금지
"""
)

st.divider()

st.subheader("최근 근무표")
if not months:
    st.info("아직 저장된 근무표가 없습니다. 왼쪽 메뉴에서 근무표를 생성해 주세요.")
else:
    month_key = months[0]
    schedule = load_schedule(month_key)
    st.write(f"최근 저장: **{month_key}**")
    if schedule:
        st.caption(f"배정 건수: {len(schedule.get('assignments', []))}")
