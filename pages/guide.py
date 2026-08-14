"""Public product guide screen."""

import streamlit as st


def guide_screen() -> None:
    st.markdown(
        '<div class="center-heading"><div class="eyebrow">HOW TO USE</div>'
        '<h1>오늘의 나에게 맞춰<br><span class="accent">작게, 다시 시작해요.</span></h1>'
        '<p>데일리 페이스가 계획을 부담이 아닌 이어갈 수 있는 습관으로 바꾸는 방법이에요.</p></div>',
        unsafe_allow_html=True,
    )

    sections = [
        ("01", "오늘 상태 체크인", "컨디션, 야근 여부, 사용할 수 있는 시간, 의욕, 수면과 한마디를 짧게 알려주세요. 정답은 없고 지금 상태 그대로 선택하면 돼요."),
        ("02", "유연한 목표 추천", "오늘의 상태와 최근 난이도 피드백을 반영해 기본·축소·최소 목표 중 하나를 추천해요. 추천 시간은 직접 수정한 뒤 수락할 수 있어요."),
        ("03", "핵심 습관 최대 3개", "운동, 공부, 독서부터 나만의 습관까지 자유롭게 등록하세요. 다만 오늘 집중할 핵심 습관은 최대 3개로 가볍게 유지해요."),
        ("04", "계획 조정과 회복", "야근, 피로, 일정 변경, 의욕 저하가 생기면 목표를 더 작게 줄이거나 휴식을 오늘의 정당한 목표로 선택할 수 있어요."),
        ("05", "기록과 복귀 기회", "완료 기록, 주간 성공률, 캘린더와 연속 달성일을 확인하세요. 하루를 놓쳐도 다음 날 돌아오면 한 번의 회복 기회로 흐름을 지켜줘요."),
        ("06", "함께 성장하는 캐릭터", "작은 습관을 완료할 때마다 동행 캐릭터가 성장해요. 완벽한 결과보다 다시 행동한 순간을 보상해요."),
        ("07", "부드러운 체크인 알림", "아침, 퇴근 전, 습관 시작 전 중 원하는 시점을 설정할 수 있어요. 놓치면 30분 뒤 한 번만 다시 알리고 더 재촉하지 않아요."),
        ("08", "내 기록과 보안", "로그인하면 기록이 기기 간 동기화돼요. 별도 앱 잠금 PIN, 데이터 내려받기와 활동 기록 초기화 기능도 제공해요."),
    ]
    for number, title, description in sections:
        st.markdown(
            f'<div class="habit-card"><div class="eyebrow">STEP {number}</div>'
            f'<h3>{title}</h3><p>{description}</p></div>',
            unsafe_allow_html=True,
        )

    st.info("체험 모드의 기록은 현재 브라우저 세션에만 유지되며 서버에는 저장되지 않아요.")
    back_col, preview_col = st.columns(2)
    if back_col.button("로그인·회원가입으로 돌아가기", use_container_width=True):
        st.session_state.show_guide = False
        st.rerun()
    if preview_col.button("회원가입 없이 체험 시작", type="primary", use_container_width=True):
        st.session_state.show_guide = False
        st.session_state.guest_mode = True
        st.session_state.nickname = "체험 사용자"
        st.session_state.page = "today"
        st.rerun()
