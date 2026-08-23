import streamlit as st

from core.storage import load_settings, save_settings


st.title("설정")

settings = load_settings()

st.subheader("필요 인원")
col1, col2 = st.columns(2)
with col1:
    weekday_day_target = st.number_input("평일 주간 목표", min_value=1, max_value=2, value=int(settings["weekday_day_target"]))
    weekday_night_target = st.number_input("평일 야간 목표", min_value=1, max_value=2, value=int(settings["weekday_night_target"]))
with col2:
    weekend_day_target = st.number_input("금/토/일 주간 목표", min_value=1, max_value=3, value=int(settings["weekend_day_target"]))
    weekend_night_target = st.number_input("금/토/일 야간 필수", min_value=2, max_value=2, value=2, disabled=True)

st.divider()
st.subheader("배치 규칙")
max_consecutive_work_days = st.number_input(
    "최대 연속 근무일",
    min_value=1,
    max_value=7,
    value=int(settings["max_consecutive_work_days"]),
)
senior_pair_rank_limit = st.number_input(
    "야간 동시 배치 금지 선임 순번",
    min_value=0,
    max_value=50,
    value=int(settings["senior_pair_rank_limit"]),
    help="예: 4로 설정하면 숙련 순번 1~4번 요원끼리는 야간에 같이 배치하지 않습니다. 0이면 끕니다.",
)

night_rest_required = st.checkbox("야간 다음날 비번 강제", value=bool(settings["night_rest_required"]))
prefer_off_after_rest = st.checkbox("비번 다음날 휴무 우선", value=bool(settings["prefer_off_after_rest"]))
prefer_day_before_night = st.checkbox("야간 전날 주간 우선", value=bool(settings["prefer_day_before_night"]))
avoid_regular_agent_pair = st.checkbox("선임끼리 야간 동시 배치 금지", value=bool(settings["avoid_regular_agent_pair"]))
avoid_limited_agent_pair = st.checkbox(
    "훈련소 미수료/교육 미수료자끼리 야간 동시 배치 금지",
    value=bool(settings["avoid_limited_agent_pair"]),
)

st.divider()
st.subheader("관리 모드")
developer_mode = st.checkbox(
    "최고권한 모드 / 개발자 모드",
    value=bool(settings.get("developer_mode", False)),
    help="켜면 요원 관리 화면에 전체 요원 데이터를 직접 수정하는 개발자 편집 표가 표시됩니다.",
)

st.divider()
solver_time_limit_seconds = st.number_input(
    "생성 제한 시간(초)",
    min_value=5,
    max_value=300,
    value=int(settings["solver_time_limit_seconds"]),
)

if st.button("설정 저장", type="primary"):
    save_settings(
        {
            "weekday_day_target": int(weekday_day_target),
            "weekend_day_target": int(weekend_day_target),
            "weekday_night_target": int(weekday_night_target),
            "weekend_night_target": int(weekend_night_target),
            "max_consecutive_work_days": int(max_consecutive_work_days),
            "senior_pair_rank_limit": int(senior_pair_rank_limit),
            "night_rest_required": bool(night_rest_required),
            "prefer_off_after_rest": bool(prefer_off_after_rest),
            "prefer_day_before_night": bool(prefer_day_before_night),
            "avoid_regular_agent_pair": bool(avoid_regular_agent_pair),
            "avoid_limited_agent_pair": bool(avoid_limited_agent_pair),
            "developer_mode": bool(developer_mode),
            "solver_time_limit_seconds": int(solver_time_limit_seconds),
        }
    )
    st.toast("설정을 저장했습니다.", icon="✅")
    st.rerun()
