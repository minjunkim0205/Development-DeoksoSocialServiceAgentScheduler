import streamlit as st


st.set_page_config(
    page_title="덕소 사회복무요원 근무표",
    page_icon="📅",
    layout="wide",
)

pages = [
    st.Page("pages/home.py", title="홈", icon="🏠"),
    st.Page("pages/agent_management.py", title="요원 관리", icon="👥"),
    st.Page("pages/schedule_generator.py", title="근무표 생성", icon="🧩"),
    st.Page("pages/schedule_editor.py", title="근무표 수정", icon="✏️"),
    st.Page("pages/settings.py", title="설정", icon="⚙️"),
]

st.navigation(pages).run()
