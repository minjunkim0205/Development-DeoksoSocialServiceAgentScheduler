import streamlit as st
from datetime import date
import pandas as pd

year:str = date.today().strftime("%Y")

WORK_TYPE_LABEL_TO_VALUE = {"일반": "general", "주간전담": "day_only", "야간전담": "night_only"}
WORK_TYPE_VALUE_TO_LABEL = {"general": "일반", "day_only": "주간전담", "night_only": "야간전담"}

from core.storage import(load_agents, save_agents)
agents = load_agents()

# ======================
# Page title
# ======================
st.title("요원 관리")

# ======================
# Agent Add
# ======================
st.header("요원 추가")
st.caption("추가시 수정할수 없는 항목은 추가후 수정 가능합니다")

with st.form("agent_add_form", clear_on_submit=True):
    name = st.text_input("이름")
    work_type_label = st.radio("근무 유형", ["일반", "주간전담", "야간전담"], disabled=True)
    is_new = st.checkbox("신입", value=True, disabled=True)
    active = st.checkbox("복무중", value=True, disabled=True)
    notes = st.text_area("메모")

    submitted = st.form_submit_button("추가")

    if submitted:
        if not name.strip():
            st.error("이름을 입력해 주세요")
        else:
            id = f"{year}{len(agents)+1:03}"
            work_type_value = WORK_TYPE_LABEL_TO_VALUE[work_type_label]

            agents.append(
                {
                    "id":id,
                    "name":name.strip(),
                    "work_type":work_type_value,
                    "is_new":is_new,
                    "active":active,
                    "notes":notes
                }
            )

            save_agents(agents)
            # st.success("추가 완료")
            st.toast("추가 완료", icon="✅")

st.divider()

# ======================
# Agent List(Edit)
# ======================
if not agents:
    st.info("요원 정보가 없습니다")
else:
    df = pd.DataFrame(agents)

    df["work_type_label"] = df["work_type"].map(WORK_TYPE_VALUE_TO_LABEL).fillna("일반")

    active_df = df[df["active"] == True].copy()
    inactive_df = df[df["active"] == False].copy()

    display_columns = [
        "id",
        "name",
        "work_type_label",
        "is_new",
        "active",
        "notes"
    ]

    st.subheader("복무중 요원")

    edited_active_df = st.data_editor(
        active_df[display_columns],
        use_container_width=True,
        num_rows="fixed",
        key="active_agents_editor",
        column_config={
            "id": st.column_config.TextColumn("관리번호", disabled=True),
            "name": st.column_config.TextColumn("이름", disabled=True),
            "work_type_label": st.column_config.SelectboxColumn(
                "근무 유형",
                options=["일반", "주간전담", "야간전담"]
            ),
            "is_new": st.column_config.CheckboxColumn("신입"),
            "active": st.column_config.CheckboxColumn("복무중"),
            "notes": st.column_config.TextColumn("메모")
        }
    )

    st.subheader("비활성 요원")

    edited_inactive_df = st.data_editor(
        inactive_df[display_columns],
        use_container_width=True,
        num_rows="fixed",
        key="inactive_agents_editor",
        column_config={
            "id": st.column_config.TextColumn("관리번호", disabled=True),
            "name": st.column_config.TextColumn("이름", disabled=True),
            "work_type_label": st.column_config.SelectboxColumn(
                "근무 유형",
                options=["일반", "주간전담", "야간전담"],
                disabled=True
            ),
            "is_new": st.column_config.CheckboxColumn("신입", disabled=True),
            "active": st.column_config.CheckboxColumn("복무중"),
            "notes": st.column_config.TextColumn("메모", disabled=True)
        }
    )

    if st.button("변경 사항 저장"):
        merged_df = pd.concat([edited_active_df, edited_inactive_df], ignore_index=True)

        merged_df["work_type"] = merged_df["work_type_label"].map(WORK_TYPE_LABEL_TO_VALUE)
        merged_df = merged_df.drop(columns=["work_type_label"])
        save_agents(merged_df.to_dict(orient="records"))

        # st.success("저장 완료")
        # st.toast("저장 완료", icon="✅")
        st.rerun()
