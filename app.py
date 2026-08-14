from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st


st.set_page_config(
    page_title="데일리 페이스",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)


@dataclass(frozen=True)
class Habit:
    key: str
    icon: str
    category: str
    title: str
    default_minutes: int
    reduced_minutes: int
    minimum_minutes: int


HABITS = [
    Habit("side_project", "✦", "성장", "사이드 프로젝트", 40, 20, 5),
    Habit("stretch", "◒", "건강", "저녁 스트레칭", 20, 10, 2),
    Habit("reading", "▤", "마음", "잠들기 전 독서", 20, 10, 5),
]

TONE_COPY = {
    "따뜻한 친구": ("오늘의 속도도 충분히 좋아요.", "지금 가능한 만큼만 해봐요."),
    "현실적인 코치": ("지속 가능한 목표가 가장 좋은 목표예요.", "오늘의 조건에 맞춰 계획을 조정했어요."),
    "짧고 단호한 트레이너": ("작게 시작하고, 확실히 끝내요.", "오늘 할 수 있는 한 가지에 집중해요."),
    "유머 있는 동료": ("야근이 등장했다! 목표가 작아졌다!", "2분도 엄연한 전진이에요."),
}


def initialize_state() -> None:
    defaults = {
        "page": "today",
        "condition": "보통",
        "overtime": "없어요",
        "available_minutes": 30,
        "motivation": "보통",
        "sleep": 6.0,
        "note": "",
        "tone": "따뜻한 친구",
        "selected_habit": "side_project",
        "completed": set(),
        "accepted": {},
        "flash": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def recommend(habit: Habit) -> dict[str, object]:
    condition = st.session_state.condition
    overtime = st.session_state.overtime == "있어요"
    motivation = st.session_state.motivation
    sleep = st.session_state.sleep
    available = st.session_state.available_minutes

    if sleep < 5 and condition == "나쁨":
        return {
            "level": "회복",
            "minutes": 0,
            "title": "오늘은 편안히 쉬기",
            "reason": "수면과 컨디션을 고려해 오늘은 회복을 우선해요.",
        }

    constraints = sum((condition == "나쁨", overtime, motivation == "낮음"))
    if constraints >= 2:
        amount = min(habit.minimum_minutes, available)
        return {
            "level": "최소",
            "minutes": amount,
            "title": f"{amount}분만 가볍게 시작하기",
            "reason": "야근과 현재 에너지를 고려해 연결만 이어갈 만큼 줄였어요.",
        }
    if constraints == 1 or available < habit.default_minutes:
        amount = max(habit.minimum_minutes, min(habit.reduced_minutes, available))
        return {
            "level": "축소",
            "minutes": amount,
            "title": f"{amount}분만 집중하기",
            "reason": "오늘 쓸 수 있는 시간 안에서 무리 없도록 조정했어요.",
        }
    return {
        "level": "기본",
        "minutes": habit.default_minutes,
        "title": f"{habit.default_minutes}분 집중하기",
        "reason": "오늘은 기본 목표를 충분히 해낼 수 있는 상태예요.",
    }


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600&display=swap');
        :root { --ink:#21342d; --muted:#718078; --paper:#f7f5ef; --dark:#385d4e; --coral:#b56856; --line:#deddd5; }
        .stApp { background:var(--paper); color:var(--ink); font-family:'Noto Sans KR',sans-serif; }
        [data-testid="stSidebar"] { background:#f0eee7; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] hr { border-color:var(--line); }
        .block-container { max-width:1120px; padding-top:2rem; padding-bottom:5rem; }
        h1,h2,h3 { color:var(--ink); font-family:'Noto Serif KR',serif!important; letter-spacing:-.035em; }
        .brand { font:600 1.35rem 'Noto Serif KR',serif; display:flex; align-items:center; gap:.65rem; margin:.2rem 0 2rem; }
        .brand-mark { display:inline-grid; place-items:center; width:31px; height:31px; border-radius:55% 45%; background:var(--dark); color:white; font-style:italic; }
        .profile { margin-top:2rem; padding:1rem; border-top:1px solid var(--line); color:var(--muted); font-size:.8rem; }
        .profile strong { color:var(--ink); display:block; font-size:.95rem; }
        .eyebrow { color:#87948d; font-size:.65rem; letter-spacing:.18em; font-weight:700; margin-bottom:.6rem; }
        .hero { min-height:315px; border-radius:28px; background:#e6e4da; padding:3.2rem 4rem; position:relative; overflow:hidden; }
        .hero h1 { font-size:2.65rem; line-height:1.25; margin:.2rem 0 1rem; }
        .hero em,.accent { color:var(--coral); font-style:normal; }
        .hero p { color:var(--muted); line-height:1.8; }
        .character { position:absolute; right:8%; bottom:-20px; width:150px; height:180px; border-radius:48% 52% 42% 45%; background:#91ad99; box-shadow:0 15px 25px #385d4e22; }
        .character:before { content:'• ᴗ •'; position:absolute; top:40px; left:24px; width:102px; height:78px; display:grid; place-items:center; border-radius:47%; background:#e5d5b8; color:#31483e; letter-spacing:.5rem; }
        .character:after { content:'천천히 해도 괜찮아'; position:absolute; right:95px; top:-32px; width:130px; padding:.65rem .8rem; border-radius:14px 14px 4px 14px; background:#fffdf7; color:#6d766f; font-size:.7rem; text-align:center; }
        .section-title { margin:2.5rem 0 1rem; }
        .section-title h2 { margin:.1rem 0; font-size:1.5rem; }
        .habit-card { min-height:235px; padding:1.35rem; background:#fbfaf6; border:1px solid var(--line); border-radius:18px; }
        .habit-icon { display:grid; place-items:center; width:40px; height:40px; border-radius:12px; background:#f3d8cc; color:#9d5e4c; font-size:1.1rem; }
        .habit-card .category { color:#9a9f9b; font-size:.65rem; margin:1rem 0 .3rem; }
        .habit-card h3 { font-size:1.05rem; margin:.2rem 0 1rem; }
        .pill { display:inline-block; background:#eeefe9; color:#65756d; border-radius:8px; padding:.4rem .6rem; font-size:.7rem; }
        .week-card,.form-card,.recommend-card { background:#fbfaf6; border:1px solid var(--line); border-radius:22px; padding:1.7rem 2rem; }
        .week-card { margin-top:1.3rem; display:flex; justify-content:space-between; align-items:center; }
        .week-card strong { color:var(--coral); font:500 2rem 'Noto Serif KR',serif; }
        .center-heading { text-align:center; max-width:650px; margin:1.2rem auto 2rem; }
        .center-heading h1 { font-size:2.35rem; line-height:1.35; }
        .center-heading p { color:var(--muted); font-size:.85rem; }
        .question-label { font:600 1rem 'Noto Serif KR',serif; margin:1.5rem 0 .4rem; }
        .question-label span { color:var(--coral); font:700 .65rem 'Noto Sans KR'; letter-spacing:.1em; margin-right:.6rem; }
        .recommend-card { max-width:760px; margin:auto; padding:2rem 2.5rem; }
        .recommend-title { display:flex; align-items:center; gap:1rem; margin:1.8rem 0; }
        .recommend-title h2 { margin:.2rem 0; }
        .reason { background:#eff0e9; color:#65746c; border-radius:13px; padding:1rem; font-size:.82rem; }
        .recovery { text-align:center; color:var(--muted); font-size:.78rem; margin:1.2rem; }
        div.stButton > button { border-radius:11px; border-color:#bdc5bf; min-height:2.8rem; }
        div.stButton > button[kind="primary"] { background:var(--dark); border-color:var(--dark); }
        [data-testid="stMetricValue"] { color:var(--coral); }
        @media(max-width:700px) {
          .block-container { padding:1rem 1rem 5rem; }
          .hero { min-height:420px; padding:2rem 1.5rem; }
          .hero h1 { font-size:2rem; }
          .character { right:-5%; transform:scale(.75); transform-origin:bottom right; }
          .week-card { display:block; }
          .center-heading { text-align:left; }
          .center-heading h1 { font-size:1.9rem; }
          .form-card,.recommend-card { padding:1.2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark">d</span>daily pace</div>', unsafe_allow_html=True)
        if st.button("⌂  오늘", use_container_width=True):
            go("today")
        if st.button("◫  기록", use_container_width=True):
            st.toast("상세 기록은 다음 버전에서 제공해요.")
        if st.button("◇  습관", use_container_width=True):
            st.toast("습관 관리는 다음 버전에서 제공해요.")
        if st.button("☆  캐릭터", use_container_width=True):
            st.toast("모리가 한 걸음씩 자라고 있어요.")
        st.divider()
        st.session_state.tone = st.selectbox("멘토 말투", list(TONE_COPY), index=list(TONE_COPY).index(st.session_state.tone))
        st.markdown('<div class="profile"><strong>민지</strong>나의 속도로, 꾸준히</div>', unsafe_allow_html=True)


def today_page() -> None:
    today = date.today()
    completed = len(st.session_state.completed)
    st.caption(f"{today.month}월 {today.day}일 · 오늘의 페이스")
    st.markdown(
        f"""<section class="hero"><div class="eyebrow">GOOD DAY</div>
        <h1>민지님, 오늘의 속도는<br><em>어떤가요?</em></h1>
        <p>완벽하지 않아도 괜찮아요.<br>지금의 나에게 맞는 한 걸음을 찾아봐요.</p>
        <div class="character"></div></section>""",
        unsafe_allow_html=True,
    )
    if st.button("오늘 체크인 시작  →", type="primary", use_container_width=True):
        go("checkin")

    st.markdown(f'<div class="section-title"><div class="eyebrow">TODAY\'S PACE</div><h2>오늘의 핵심 습관 · {completed}/3 완료</h2></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for col, habit in zip(cols, HABITS):
        with col:
            done = habit.key in st.session_state.completed
            suggested = st.session_state.accepted.get(habit.key, habit.reduced_minutes)
            st.markdown(
                f"""<div class="habit-card"><span class="habit-icon">{habit.icon}</span>
                <div class="category">{habit.category}</div><h3>{habit.title}</h3>
                <span class="pill">오늘 추천 · {suggested}분</span><p>{'✓ 완료했어요' if done else '작게 시작해도 충분해요'}</p></div>""",
                unsafe_allow_html=True,
            )
            if st.button("완료 취소" if done else "완료 기록", key=f"done-{habit.key}", use_container_width=True):
                if done:
                    st.session_state.completed.remove(habit.key)
                else:
                    st.session_state.completed.add(habit.key)
                st.rerun()
            if st.button("목표 조정", key=f"adjust-{habit.key}", use_container_width=True):
                st.session_state.selected_habit = habit.key
                go("recommendation")

    st.markdown(
        """<div class="week-card"><div><div class="eyebrow">THIS WEEK</div>
        <h3>이번 주도 잘 돌아오고 있어요</h3><small>하루를 놓쳐도 다시 시작한 날이 2번이나 있었어요.</small></div>
        <div><strong>72%</strong><br><small>주간 달성률</small></div></div>""",
        unsafe_allow_html=True,
    )


def checkin_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">DAILY CHECK-IN</div><h1>지금의 나를<br><span class="accent">가볍게 알려주세요.</span></h1><p>솔직할수록 오늘에 맞는 목표를 찾기 쉬워져요.</p></div>', unsafe_allow_html=True)
    left, center, right = st.columns([1, 7, 1])
    with center:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="question-label"><span>01</span>오늘 컨디션은 어떤가요?</div>', unsafe_allow_html=True)
        st.session_state.condition = st.segmented_control("컨디션", ["좋음", "보통", "나쁨"], default=st.session_state.condition, label_visibility="collapsed")
        st.markdown('<div class="question-label"><span>02</span>오늘 야근이 있나요?</div>', unsafe_allow_html=True)
        st.session_state.overtime = st.segmented_control("야근", ["없어요", "있어요"], default=st.session_state.overtime, label_visibility="collapsed")
        st.markdown('<div class="question-label"><span>03</span>습관에 쓸 수 있는 시간은요?</div>', unsafe_allow_html=True)
        st.session_state.available_minutes = st.select_slider("가용 시간", options=[5, 10, 15, 20, 30, 45, 60], value=st.session_state.available_minutes, format_func=lambda v: f"{v}분")
        st.markdown('<div class="question-label"><span>04</span>지금 의욕은 어느 정도인가요?</div>', unsafe_allow_html=True)
        st.session_state.motivation = st.segmented_control("의욕", ["낮음", "보통", "높음"], default=st.session_state.motivation, label_visibility="collapsed")
        st.markdown('<div class="question-label"><span>05</span>어젯밤에는 얼마나 잤나요?</div>', unsafe_allow_html=True)
        st.session_state.sleep = st.slider("수면 시간", 3.0, 9.0, st.session_state.sleep, 0.5, format="%.1f시간")
        st.session_state.note = st.text_area("오늘의 한마디 (선택)", st.session_state.note, placeholder="예: 회의가 길어서 머리가 조금 복잡해요", max_chars=120)
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("나에게 맞는 목표 보기  →", type="primary", use_container_width=True):
            st.session_state.selected_habit = HABITS[0].key
            go("recommendation")


def recommendation_page() -> None:
    habit = next(h for h in HABITS if h.key == st.session_state.selected_habit)
    suggestion = recommend(habit)
    if st.button("← 체크인 수정하기"):
        go("checkin")
    title, subtitle = TONE_COPY[st.session_state.tone]
    st.markdown(f'<div class="center-heading"><div class="eyebrow">TODAY\'S RECOMMENDATION</div><h1>오늘은 이만큼이면<br><span class="accent">충분해요.</span></h1><p>{title} {subtitle}</p></div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="recommend-card"><span class="pill">{suggestion['level']} 목표 · {habit.category}</span>
        <div class="recommend-title"><span class="habit-icon">{habit.icon}</span><div><small>{habit.title}</small><h2>{suggestion['title']}</h2></div></div>
        <div class="reason"><strong>이렇게 추천한 이유</strong><br>{suggestion['reason']}</div></div>""",
        unsafe_allow_html=True,
    )
    custom = st.slider("목표 시간 수정", 0, 60, int(suggestion["minutes"]), 1, format="%d분")
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("다시 체크인", use_container_width=True):
            go("checkin")
    with col2:
        if st.button("이 목표로 할게요  →", type="primary", use_container_width=True):
            st.session_state.accepted[habit.key] = custom
            st.session_state.flash = f"{habit.title} 목표를 오늘 계획에 담았어요."
            go("today")
    st.markdown('<div class="recovery">♡ 하루 쉬어도 기록은 사라지지 않아요. 내일 돌아오면 연속 기록을 이어드릴게요.</div>', unsafe_allow_html=True)


initialize_state()
inject_styles()
sidebar()
if st.session_state.flash:
    st.toast(st.session_state.flash, icon="🌿")
    st.session_state.flash = ""

if st.session_state.page == "checkin":
    checkin_page()
elif st.session_state.page == "recommendation":
    recommendation_page()
else:
    today_page()

