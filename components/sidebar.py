"""Shared authenticated sidebar."""

from html import escape

import streamlit as st


def render_sidebar(go, is_admin, display_name) -> None:
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark">d</span>daily pace</div>', unsafe_allow_html=True)
        if st.button("⌂  오늘", use_container_width=True):
            go("today")
        if st.button("◫  기록", use_container_width=True):
            go("records")
        if st.button("◇  습관", use_container_width=True):
            go("habits")
        if st.button("☆  캐릭터", use_container_width=True):
            go("character")
        if st.button("⚿  앱 잠금", use_container_width=True):
            go("security")
        if st.button("⚙  프로필 설정", use_container_width=True):
            go("profile")
        if st.button("◷  알림 설정", use_container_width=True):
            go("reminders")
        if st.button("⇩  내 데이터", use_container_width=True):
            go("data")
        if is_admin() and st.button("▦  운영 지표", use_container_width=True):
            go("admin")
        st.divider()
        st.caption(f"멘토 말투 · {st.session_state.tone}")
        st.markdown(f'<div class="profile"><strong>{escape(display_name())}</strong>나의 속도로, 꾸준히</div>', unsafe_allow_html=True)
        if st.session_state.guest_mode:
            st.info("체험 모드예요. 현재 기록은 브라우저 세션에만 유지되며 서버에 저장되지 않아요.")
            if st.button("가입하고 기록 저장하기", type="primary", use_container_width=True):
                st.session_state.guest_mode = False
                st.session_state.page = "today"
                st.rerun()
        if st.session_state.auth and st.button("로그아웃", use_container_width=True):
            st.session_state.auth = None
            st.session_state.admin_metrics = None
            st.session_state.remote_loaded = False
            st.session_state.app_unlocked = False
            st.rerun()
