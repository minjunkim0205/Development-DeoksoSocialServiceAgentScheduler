from datetime import date

import pandas as pd
import streamlit as st

from core.scheduler import WORK_TYPE_LABELS
from core.storage import load_agents, load_settings, save_agents


WORK_TYPE_LABEL_TO_VALUE = {label: value for value, label in WORK_TYPE_LABELS.items()}
WORK_TYPE_OPTIONS = list(WORK_TYPE_LABEL_TO_VALUE.keys())


def next_agent_id(agents: list[dict]) -> str:
    year = date.today().strftime("%Y")
    same_year_ids = [
        int(str(agent.get("id", ""))[4:])
        for agent in agents
        if str(agent.get("id", "")).startswith(year) and str(agent.get("id", ""))[4:].isdigit()
    ]
    return f"{year}{(max(same_year_ids, default=0) + 1):03}"


def normalize_agent(agent: dict, index: int) -> dict:
    return {
        "id": str(agent.get("id") or ""),
        "name": str(agent.get("name") or ""),
        "seniority_rank": agent.get("seniority_rank") or index,
        "work_type": agent.get("work_type") or "general",
        "pre_service": bool(agent.get("pre_service", False)),
        "training_completed": bool(agent.get("training_completed", True)),
        "active": bool(agent.get("active", True)),
        "notes": str(agent.get("notes") or ""),
    }


def id_sort_key(agent: dict) -> tuple[int, str]:
    agent_id = str(agent.get("id", ""))
    return (int(agent_id) if agent_id.isdigit() else 999999999, agent_id)


def apply_active_seniority(agents: list[dict]) -> list[dict]:
    normalized = [{**agent, "seniority_rank": None} for agent in agents]
    active_agents = sorted(
        [agent for agent in normalized if agent.get("active") is True],
        key=id_sort_key,
    )
    rank_by_id = {
        str(agent["id"]): rank
        for rank, agent in enumerate(active_agents, start=1)
    }

    for agent in normalized:
        if agent.get("active") is True:
            agent["seniority_rank"] = rank_by_id[str(agent["id"])]

    return sorted(
        normalized,
        key=lambda agent: (
            0 if agent.get("active") is True else 1,
            int(agent["seniority_rank"] or 9999),
            id_sort_key(agent),
        ),
    )


def dataframe_from_agents(agents: list[dict], include_delete: bool) -> pd.DataFrame:
    base_columns = [
        "id",
        "seniority_rank",
        "name",
        "work_type",
        "pre_service",
        "training_completed",
        "active",
        "notes",
    ]
    if not agents:
        columns = [*base_columns, "work_type_label", "boot_camp_completed"]
        if include_delete:
            columns.append("delete")
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(agents)
    df["work_type_label"] = df["work_type"].map(WORK_TYPE_LABELS).fillna("일반")
    df["boot_camp_completed"] = ~df["pre_service"].astype(bool)
    if include_delete:
        df["delete"] = False
    return df


def records_from_editor(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    result = df.copy()
    if "delete" in result.columns:
        result = result[result["delete"] == False].drop(columns=["delete"])

    result["work_type"] = result["work_type_label"].map(WORK_TYPE_LABEL_TO_VALUE)
    result["pre_service"] = ~result["boot_camp_completed"].astype(bool)
    result["id"] = result["id"].astype(str)
    result["name"] = result["name"].fillna("").astype(str).str.strip()
    result["notes"] = result["notes"].fillna("").astype(str)
    result = result.drop(columns=["work_type_label", "boot_camp_completed"])
    return result.to_dict(orient="records")


def editor_config(allow_delete: bool) -> dict:
    config = {
        "id": st.column_config.TextColumn("관리번호", disabled=True),
        "seniority_rank": st.column_config.NumberColumn("숙련 순번", disabled=True),
        "name": st.column_config.TextColumn("이름", required=True),
        "work_type_label": st.column_config.SelectboxColumn("근무 유형", options=WORK_TYPE_OPTIONS, required=True),
        "boot_camp_completed": st.column_config.CheckboxColumn("훈련소 수료"),
        "training_completed": st.column_config.CheckboxColumn("교육 수료"),
        "active": st.column_config.CheckboxColumn("복무 중"),
        "notes": st.column_config.TextColumn("메모"),
    }
    if allow_delete:
        config["delete"] = st.column_config.CheckboxColumn("삭제")
    return config


def developer_edit_enabled() -> bool:
    return load_settings().get("developer_mode") is True or st.query_params.get("dev_edit") == "1"


def render_developer_editor(agents: list[dict]) -> None:
    st.divider()
    st.subheader("개발자 편집")
    st.caption("전체 요원 데이터를 직접 수정합니다. 삭제 체크가 켜진 행은 저장 시 제거됩니다.")

    dev_columns = [
        "delete",
        "id",
        "seniority_rank",
        "name",
        "work_type",
        "pre_service",
        "training_completed",
        "active",
        "notes",
    ]
    dev_df = pd.DataFrame(agents)
    for column in dev_columns:
        if column not in dev_df.columns:
            dev_df[column] = False if column in ["delete", "pre_service"] else ""
    dev_df["delete"] = False

    edited_dev_df = st.data_editor(
        dev_df[dev_columns],
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "delete": st.column_config.CheckboxColumn("삭제"),
            "id": st.column_config.TextColumn("관리번호", required=True),
            "seniority_rank": st.column_config.NumberColumn("숙련 순번", disabled=True),
            "name": st.column_config.TextColumn("이름", required=True),
            "work_type": st.column_config.SelectboxColumn("근무 유형", options=list(WORK_TYPE_LABELS.keys()), required=True),
            "pre_service": st.column_config.CheckboxColumn("훈련소 미수료"),
            "training_completed": st.column_config.CheckboxColumn("교육 수료"),
            "active": st.column_config.CheckboxColumn("복무 중"),
            "notes": st.column_config.TextColumn("메모"),
        },
        key="developer_agents_editor",
    )

    if st.button("개발자 편집 저장", type="primary"):
        result = edited_dev_df[edited_dev_df["delete"] == False].drop(columns=["delete"]).copy()
        result["id"] = result["id"].fillna("").astype(str).str.strip()
        result["name"] = result["name"].fillna("").astype(str).str.strip()
        result["work_type"] = result["work_type"].fillna("general").astype(str)
        result["pre_service"] = result["pre_service"].fillna(False).astype(bool)
        result["training_completed"] = result["training_completed"].fillna(True).astype(bool)
        result["active"] = result["active"].fillna(True).astype(bool)
        result["notes"] = result["notes"].fillna("").astype(str)

        if result["id"].eq("").any():
            st.error("관리번호가 비어 있는 행이 있습니다.")
        elif result["id"].duplicated().any():
            st.error("관리번호가 중복된 행이 있습니다.")
        elif result["name"].eq("").any():
            st.error("이름이 비어 있는 행이 있습니다.")
        else:
            records = result.to_dict(orient="records")
            save_agents(apply_active_seniority(records))
            st.toast("개발자 편집 내용을 저장했습니다.", icon="✅")
            st.rerun()


st.title("요원 관리")

agents = apply_active_seniority(
    [normalize_agent(agent, index) for index, agent in enumerate(load_agents(), start=1)]
)

if developer_edit_enabled():
    render_developer_editor(agents)

with st.form("agent_add_form", clear_on_submit=True):
    st.subheader("요원 추가")
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("이름")
    with col2:
        work_type_label = st.selectbox("근무 유형", WORK_TYPE_OPTIONS)

    col3, col4, col5 = st.columns(3)
    with col3:
        boot_camp_completed = st.checkbox("훈련소 수료", value=False)
    with col4:
        training_completed = st.checkbox("교육 수료", value=False)
    with col5:
        active = st.checkbox("복무 중", value=True)

    notes = st.text_area("메모")
    submitted = st.form_submit_button("추가", type="primary")

    if submitted:
        if not name.strip():
            st.error("이름을 입력해 주세요.")
        else:
            agents.append(
                {
                    "id": next_agent_id(agents),
                    "name": name.strip(),
                    "seniority_rank": None,
                    "work_type": WORK_TYPE_LABEL_TO_VALUE[work_type_label],
                    "pre_service": not boot_camp_completed,
                    "training_completed": training_completed,
                    "active": active,
                    "notes": notes.strip(),
                }
            )
            save_agents(apply_active_seniority(agents))
            st.toast("요원을 추가했습니다.", icon="✅")
            st.rerun()

st.divider()

if not agents:
    st.info("등록된 요원이 없습니다.")
    st.stop()

active_agents = [agent for agent in agents if agent.get("active") is True]
inactive_agents = [agent for agent in agents if agent.get("active") is not True]

active_columns = [
    "id",
    "seniority_rank",
    "name",
    "work_type_label",
    "boot_camp_completed",
    "training_completed",
    "active",
    "notes",
]
inactive_columns = ["delete", *active_columns]

st.subheader("복무 중")
active_df = dataframe_from_agents(active_agents, include_delete=False)
if active_agents:
    edited_active_df = st.data_editor(
        active_df[active_columns],
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config=editor_config(allow_delete=False),
        key="active_agents_editor",
    )
else:
    edited_active_df = pd.DataFrame(columns=active_columns)
    st.info("복무 중인 요원이 없습니다.")

st.subheader("복무 해제")
if inactive_agents:
    inactive_df = dataframe_from_agents(inactive_agents, include_delete=True)
    edited_inactive_df = st.data_editor(
        inactive_df[inactive_columns],
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config=editor_config(allow_delete=True),
        key="inactive_agents_editor",
    )
else:
    edited_inactive_df = pd.DataFrame(columns=inactive_columns)
    st.info("복무 해제된 요원이 없습니다.")

if st.button("변경사항 저장", type="primary"):
    edited_active_df["active"] = edited_active_df["active"].astype(bool)
    if not edited_inactive_df.empty:
        edited_inactive_df["active"] = edited_inactive_df["active"].astype(bool)

    delete_count = int(edited_inactive_df["delete"].sum()) if "delete" in edited_inactive_df.columns else 0
    records = records_from_editor(edited_active_df) + records_from_editor(edited_inactive_df)

    if any(not record["name"] for record in records):
        st.error("이름이 비어 있는 요원이 있습니다.")
    else:
        save_agents(apply_active_seniority(records))
        if delete_count:
            st.toast(f"복무 해제 요원 {delete_count}명을 삭제하고 저장했습니다.", icon="✅")
        else:
            st.toast("저장했습니다.", icon="✅")
        st.rerun()
