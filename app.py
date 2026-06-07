import streamlit as st

st.set_page_config(
    page_title="사회복무 요원 근무 스케줄러",
    page_icon="📅",
    layout="wide"
)

pg = st.navigation(
    [
        st.Page(
            "pages/home.py",
            title="메인",
            icon="🏠"
        ),
        st.Page(
            "pages/agent_management.py",
            title="요원 관리",
            icon="👥"
        ),
        st.Page(
            "pages/schedule_generator.py",
            title="근무표 생성",
            icon="📅"
        ),
        st.Page(
            "pages/schedule_editor.py",
            title="근무표 수정",
            icon="✏️"
        ),
        st.Page(
            "pages/settings.py",
            title="설정",
            icon="⚙️"
        )
    ]
)

pg.run()