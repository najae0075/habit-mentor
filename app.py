from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from html import escape
from secrets import token_hex
from uuid import uuid4

import streamlit as st

from supabase_backend import SupabaseBackend, SupabaseError


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


def habit_to_dict(habit: Habit) -> dict[str, object]:
    return {
        "key": habit.key,
        "icon": habit.icon,
        "category": habit.category,
        "title": habit.title,
        "default_minutes": habit.default_minutes,
        "reduced_minutes": habit.reduced_minutes,
        "minimum_minutes": habit.minimum_minutes,
    }


def all_habits() -> list[Habit]:
    custom = [Habit(**item) for item in st.session_state.custom_habits]
    return [*HABITS, *custom]


def focused_habits() -> list[Habit]:
    selected = set(st.session_state.focus_habits)
    return [habit for habit in all_habits() if habit.key in selected][:3]

TONE_COPY = {
    "따뜻한 친구": ("오늘의 속도도 충분히 좋아요.", "지금 가능한 만큼만 해봐요."),
    "현실적인 코치": ("지속 가능한 목표가 가장 좋은 목표예요.", "오늘의 조건에 맞춰 계획을 조정했어요."),
    "짧고 단호한 트레이너": ("작게 시작하고, 확실히 끝내요.", "오늘 할 수 있는 한 가지에 집중해요."),
    "유머 있는 동료": ("야근이 등장했다! 목표가 작아졌다!", "2분도 엄연한 전진이에요."),
}

PUBLIC_APP_URL = "https://habit-mentor-najae0075.streamlit.app/"


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
        "nickname": "나",
        "selected_habit": "side_project",
        "completed": set(),
        "completion_history": {},
        "focus_history": {},
        "checkin_dates": [],
        "active_date": date.today().isoformat(),
        "adjustment_history": {},
        "rest_history": {},
        "app_lock": None,
        "app_unlocked": False,
        "accepted": {},
        "custom_habits": [],
        "focus_habits": [habit.key for habit in HABITS],
        "flash": "",
        "auth": None,
        "remote_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_backend() -> SupabaseBackend | None:
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_ANON_KEY", "")
    except FileNotFoundError:
        return None
    return SupabaseBackend(url, key) if url and key else None


def serializable_state() -> dict[str, object]:
    return {
        "condition": st.session_state.condition,
        "overtime": st.session_state.overtime,
        "available_minutes": st.session_state.available_minutes,
        "motivation": st.session_state.motivation,
        "sleep": st.session_state.sleep,
        "note": st.session_state.note,
        "tone": st.session_state.tone,
        "nickname": st.session_state.nickname,
        "completed": sorted(st.session_state.completed),
        "completion_history": st.session_state.completion_history,
        "focus_history": st.session_state.focus_history,
        "checkin_dates": st.session_state.checkin_dates,
        "active_date": st.session_state.active_date,
        "adjustment_history": st.session_state.adjustment_history,
        "rest_history": st.session_state.rest_history,
        "app_lock": st.session_state.app_lock,
        "accepted": st.session_state.accepted,
        "custom_habits": st.session_state.custom_habits,
        "focus_habits": st.session_state.focus_habits,
    }


def save_remote() -> None:
    backend = get_backend()
    auth = st.session_state.auth
    if not backend or not auth:
        return
    try:
        backend.save_state(auth["user"]["id"], auth["access_token"], serializable_state())
    except SupabaseError as error:
        st.toast(str(error), icon="⚠️")


def load_remote() -> None:
    backend = get_backend()
    auth = st.session_state.auth
    if not backend or not auth or st.session_state.remote_loaded:
        return
    try:
        saved = backend.load_state(auth["user"]["id"], auth["access_token"])
    except SupabaseError as error:
        st.error(f"저장된 기록을 불러오지 못했습니다: {error}")
        return
    if saved:
        for key in ("condition", "overtime", "available_minutes", "motivation", "sleep", "note", "tone", "nickname", "accepted", "custom_habits", "focus_habits", "completion_history", "focus_history", "checkin_dates", "active_date", "adjustment_history", "rest_history", "app_lock"):
            if key in saved:
                st.session_state[key] = saved[key]
        st.session_state.completed = set(saved.get("completed", []))
    today_key = date.today().isoformat()
    if st.session_state.active_date != today_key:
        st.session_state.completed = set(st.session_state.completion_history.get(today_key, []))
        st.session_state.active_date = today_key
    st.session_state.remote_loaded = True


def record_today() -> None:
    today_key = date.today().isoformat()
    st.session_state.active_date = today_key
    st.session_state.completion_history[today_key] = sorted(st.session_state.completed)
    st.session_state.focus_history[today_key] = list(st.session_state.focus_habits)


def weekly_stats() -> tuple[int, int, int]:
    today = date.today()
    dates = [(today - timedelta(days=offset)).isoformat() for offset in range(7)]
    completed_count = 0
    target_count = 0
    for day in dates:
        focus = set(st.session_state.focus_history.get(day, []))
        focus -= set(st.session_state.rest_history.get(day, []))
        completed = set(st.session_state.completion_history.get(day, []))
        completed_count += len(completed & focus)
        target_count += len(focus)
    success_rate = round(completed_count / target_count * 100) if target_count else 0

    streak, _ = streak_details()
    return success_rate, streak, len(set(st.session_state.checkin_dates) & set(dates))


def streak_details() -> tuple[int, str | None]:
    cursor = date.today()
    today_key = cursor.isoformat()
    if not st.session_state.completion_history.get(today_key) and not st.session_state.rest_history.get(today_key):
        cursor -= timedelta(days=1)

    streak = 0
    recovery_day = None
    recovery_candidate = None
    for _ in range(366):
        day_key = cursor.isoformat()
        completed = bool(st.session_state.completion_history.get(day_key))
        planned_rest = bool(st.session_state.rest_history.get(day_key))
        if completed or planned_rest:
            streak += 1
            if recovery_candidate:
                recovery_day = recovery_candidate
                recovery_candidate = None
        elif streak and recovery_day is None and recovery_candidate is None:
            recovery_candidate = day_key
        else:
            break
        cursor -= timedelta(days=1)
    return streak, recovery_day


def character_stats() -> tuple[int, str, int, int]:
    points = sum(len(set(items)) for items in st.session_state.completion_history.values())
    stages = [(0, "새싹 모리"), (5, "한 뼘 모리"), (15, "튼튼 모리"), (30, "빛나는 모리")]
    level = 1
    name = stages[0][1]
    next_goal = stages[1][0]
    for index, (threshold, stage_name) in enumerate(stages):
        if points >= threshold:
            level = index + 1
            name = stage_name
            next_goal = stages[index + 1][0] if index + 1 < len(stages) else threshold
    return points, name, level, next_goal


def pin_digest(pin: str, salt: str) -> str:
    return pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 310_000).hex()


def valid_pin(pin: str) -> bool:
    lock = st.session_state.app_lock
    if not lock:
        return False
    return compare_digest(pin_digest(pin, lock["salt"]), lock["digest"])


def display_name() -> str:
    nickname = st.session_state.nickname.strip()
    if nickname:
        return nickname
    auth = st.session_state.auth or {}
    email = auth.get("user", {}).get("email", "")
    return email.split("@", 1)[0] if email else "나"


def auth_screen(backend: SupabaseBackend) -> None:
    st.markdown('<div class="center-heading"><div class="eyebrow">WELCOME</div><h1>나의 속도를<br><span class="accent">안전하게 기록해요.</span></h1><p>로그인하면 다른 기기에서도 습관 기록을 이어갈 수 있어요.</p></div>', unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        mode = st.segmented_control("인증 방식", ["로그인", "회원가입"], default="로그인")
        email = st.text_input("이메일", placeholder="name@example.com")
        password = st.text_input("비밀번호", type="password", help="8자 이상 입력해주세요.")
        if st.button(mode, type="primary", use_container_width=True):
            if "@" not in email or len(password) < 8:
                st.warning("올바른 이메일과 8자 이상의 비밀번호를 입력해주세요.")
                return
            try:
                if mode == "로그인":
                    result = backend.sign_in(email, password)
                else:
                    try:
                        result = backend.sign_up(email, password, redirect_to=PUBLIC_APP_URL)
                    except TypeError as error:
                        # Streamlit can briefly retain the previous imported module
                        # while applying a rolling deployment. The configured
                        # Supabase Site URL remains the safe fallback redirect.
                        if "redirect_to" not in str(error):
                            raise
                        result = backend.sign_up(email, password)
            except SupabaseError as error:
                st.error(str(error))
                return
            if result.get("access_token"):
                st.session_state.auth = result
                st.session_state.remote_loaded = False
                st.rerun()
            else:
                st.success("확인 이메일을 보냈어요. 이메일 인증 후 로그인해주세요.")


def lock_screen() -> None:
    st.markdown('<div class="center-heading"><div class="eyebrow">APP LOCK</div><h1>나만의 기록을<br><span class="accent">안전하게 잠갔어요.</span></h1><p>설정한 앱 잠금 PIN을 입력해주세요.</p></div>', unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.2, 1])
    with center, st.form("unlock-app"):
        pin = st.text_input("앱 잠금 PIN", type="password", max_chars=6)
        if st.form_submit_button("잠금 해제", type="primary", use_container_width=True):
            if valid_pin(pin):
                st.session_state.app_unlocked = True
                st.rerun()
            else:
                st.error("PIN이 올바르지 않아요.")


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
        .character-stage { display:grid; place-items:center; min-height:260px; margin:1rem 0 2rem; border-radius:24px; background:#e6e4da; }
        .character-avatar { display:grid; place-items:center; width:150px; height:170px; border-radius:48% 52% 42% 45%; background:#91ad99; color:#31483e; font-size:2rem; box-shadow:0 15px 25px #385d4e22; }
        .badge-card { min-height:125px; padding:1.1rem; border:1px solid var(--line); border-radius:16px; background:#fbfaf6; }
        .badge-card.locked { opacity:.45; filter:grayscale(1); }
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
            go("records")
        if st.button("◇  습관", use_container_width=True):
            go("habits")
        if st.button("☆  캐릭터", use_container_width=True):
            go("character")
        if st.button("⚿  앱 잠금", use_container_width=True):
            go("security")
        if st.button("⚙  프로필 설정", use_container_width=True):
            go("profile")
        st.divider()
        st.caption(f"멘토 말투 · {st.session_state.tone}")
        st.markdown(f'<div class="profile"><strong>{escape(display_name())}</strong>나의 속도로, 꾸준히</div>', unsafe_allow_html=True)
        if st.session_state.auth and st.button("로그아웃", use_container_width=True):
            st.session_state.auth = None
            st.session_state.remote_loaded = False
            st.session_state.app_unlocked = False
            st.rerun()


def today_page() -> None:
    today = date.today()
    name = escape(display_name())
    completed = len(set(st.session_state.completed) & set(st.session_state.focus_habits))
    st.caption(f"{today.month}월 {today.day}일 · 오늘의 페이스")
    st.markdown(
        f"""<section class="hero"><div class="eyebrow">GOOD DAY</div>
        <h1>{name}님, 오늘의 속도는<br><em>어떤가요?</em></h1>
        <p>완벽하지 않아도 괜찮아요.<br>지금의 나에게 맞는 한 걸음을 찾아봐요.</p>
        <div class="character"></div></section>""",
        unsafe_allow_html=True,
    )
    if st.button("오늘 체크인 시작  →", type="primary", use_container_width=True):
        go("checkin")

    daily_habits = focused_habits()
    st.markdown(f'<div class="section-title"><div class="eyebrow">TODAY\'S PACE</div><h2>오늘의 핵심 습관 · {completed}/{len(daily_habits)} 완료</h2></div>', unsafe_allow_html=True)
    if not daily_habits:
        st.info("오늘 집중할 습관을 선택해주세요.")
        if st.button("핵심 습관 선택하기"):
            go("habits")
        return
    cols = st.columns(len(daily_habits))
    today_key = date.today().isoformat()
    rested_today = set(st.session_state.rest_history.get(today_key, []))
    for col, habit in zip(cols, daily_habits):
        with col:
            done = habit.key in st.session_state.completed
            resting = habit.key in rested_today
            suggested = st.session_state.accepted.get(habit.key, habit.reduced_minutes)
            target_label = "오늘은 회복하기" if resting else f"오늘 추천 · {suggested}분"
            status_label = "휴식도 오늘의 목표예요" if resting else ('✓ 완료했어요' if done else '작게 시작해도 충분해요')
            st.markdown(
                f"""<div class="habit-card"><span class="habit-icon">{habit.icon}</span>
                <div class="category">{habit.category}</div><h3>{habit.title}</h3>
                <span class="pill">{target_label}</span><p>{status_label}</p></div>""",
                unsafe_allow_html=True,
            )
            if st.button("완료 취소" if done else "완료 기록", key=f"done-{habit.key}", use_container_width=True):
                if done:
                    st.session_state.completed.remove(habit.key)
                else:
                    st.session_state.completed.add(habit.key)
                    if habit.key in rested_today:
                        st.session_state.rest_history[today_key] = [key for key in rested_today if key != habit.key]
                record_today()
                save_remote()
                st.rerun()
            if st.button("목표 조정", key=f"adjust-{habit.key}", use_container_width=True):
                st.session_state.selected_habit = habit.key
                go("recommendation")
            if st.button("오늘 어려워요", key=f"quick-{habit.key}", use_container_width=True):
                st.session_state.selected_habit = habit.key
                go("quick_adjust")

    success_rate, streak, _ = weekly_stats()
    _, recovery_day = streak_details()
    recovery_copy = "복귀 기회로 연속 기록을 지켰어요." if recovery_day else "하루를 놓쳐도 다음 날 돌아오면 기록을 지켜드려요."
    st.markdown(
        f"""<div class="week-card"><div><div class="eyebrow">THIS WEEK</div>
        <h3>이번 주도 잘 돌아오고 있어요</h3><small>현재 연속 달성 {streak}일 · {recovery_copy}</small></div>
        <div><strong>{success_rate}%</strong><br><small>주간 성공률</small></div></div>""",
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
            daily_habits = focused_habits()
            if not daily_habits:
                st.warning("먼저 오늘의 핵심 습관을 선택해주세요.")
                return
            st.session_state.selected_habit = daily_habits[0].key
            today_key = date.today().isoformat()
            if today_key not in st.session_state.checkin_dates:
                st.session_state.checkin_dates.append(today_key)
            save_remote()
            go("recommendation")


def recommendation_page() -> None:
    habit = next((h for h in all_habits() if h.key == st.session_state.selected_habit), None)
    if habit is None:
        st.warning("추천할 습관이 없습니다. 먼저 핵심 습관을 선택해주세요.")
        if st.button("습관 선택하기"):
            go("habits")
        return
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
            save_remote()
            go("today")
    st.markdown('<div class="recovery">♡ 하루 쉬어도 기록은 사라지지 않아요. 내일 돌아오면 연속 기록을 이어드릴게요.</div>', unsafe_allow_html=True)


def quick_adjust_page() -> None:
    habit = next((item for item in all_habits() if item.key == st.session_state.selected_habit), None)
    if habit is None:
        st.warning("조정할 습관을 찾지 못했어요.")
        return
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown(f'<div class="center-heading"><div class="eyebrow">QUICK RESET</div><h1>계획이 달라져도<br><span class="accent">포기한 건 아니에요.</span></h1><p>{habit.title}을 지금 상황에 맞게 다시 조정해요.</p></div>', unsafe_allow_html=True)

    reason = st.segmented_control(
        "무엇이 달라졌나요?",
        ["야근", "피로", "일정 변경", "의욕 저하"],
        default="야근",
    )
    st.info(f"{reason}이 있는 날에는 {habit.minimum_minutes}분의 최소 목표나 충분한 휴식을 추천해요.")
    reduce_col, rest_col = st.columns(2)
    if reduce_col.button(f"{habit.minimum_minutes}분으로 줄이기", type="primary", use_container_width=True):
        today_key = date.today().isoformat()
        st.session_state.accepted[habit.key] = habit.minimum_minutes
        st.session_state.adjustment_history.setdefault(today_key, {})[habit.key] = reason
        st.session_state.rest_history[today_key] = [key for key in st.session_state.rest_history.get(today_key, []) if key != habit.key]
        record_today()
        save_remote()
        st.session_state.flash = "오늘 가능한 최소 목표로 조정했어요. 이것도 충분한 전진이에요."
        go("today")
    if rest_col.button("오늘은 회복하기", use_container_width=True):
        today_key = date.today().isoformat()
        rested = set(st.session_state.rest_history.get(today_key, []))
        rested.add(habit.key)
        st.session_state.rest_history[today_key] = sorted(rested)
        st.session_state.adjustment_history.setdefault(today_key, {})[habit.key] = reason
        st.session_state.completed.discard(habit.key)
        record_today()
        save_remote()
        st.session_state.flash = "휴식을 오늘의 목표로 정했어요. 회복도 꾸준함의 일부예요."
        go("today")


def records_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">MY RECORDS</div><h1>완벽함보다 중요한 건<br><span class="accent">다시 돌아온 기록이에요.</span></h1><p>작은 실천과 체크인이 쌓인 지난 7일을 확인해보세요.</p></div>', unsafe_allow_html=True)

    success_rate, streak, checkin_days = weekly_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("주간 성공률", f"{success_rate}%")
    col2.metric("연속 달성일", f"{streak}일")
    col3.metric("주간 체크인", f"{checkin_days}/7일")
    _, recovery_day = streak_details()
    if recovery_day:
        recovered = date.fromisoformat(recovery_day)
        st.success(f"♡ {recovered.month}/{recovered.day}의 공백은 복귀 기회로 연결했어요. 연속 기록은 안전해요.")
    else:
        st.caption("하루를 놓쳐도 다음 날 돌아오면 한 번의 복귀 기회로 연속 기록을 이어드려요.")

    st.subheader("최근 7일")
    habits = {habit.key: habit for habit in all_habits()}
    today = date.today()
    for offset in range(7):
        day = today - timedelta(days=offset)
        day_key = day.isoformat()
        focus = st.session_state.focus_history.get(day_key, [])
        completed = set(st.session_state.completion_history.get(day_key, []))
        rested = set(st.session_state.rest_history.get(day_key, []))
        labels = [habits[key].title for key in focus if key in completed and key in habits]
        labels.extend(f"{habits[key].title} (회복)" for key in focus if key in rested and key in habits)
        checked_in = day_key in st.session_state.checkin_dates
        status = " · ".join(labels) if labels else "기록 없음"
        checkin_badge = "체크인 완료" if checked_in else "체크인 없음"
        st.markdown(f"**{day.month}/{day.day}** · {checkin_badge}  \n{status}")
        st.divider()

    if success_rate == 0:
        st.info("아직 괜찮아요. 오늘 단 하나의 작은 습관부터 기록해보세요.")
    elif success_rate < 70:
        st.success("흐름을 만들고 있어요. 놓친 날보다 다시 시작한 날을 기억해요.")
    else:
        st.success("꾸준한 흐름이 보여요. 지금의 현실적인 속도를 유지해보세요.")


def character_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    points, stage_name, level, next_goal = character_stats()
    st.markdown(f'<div class="center-heading"><div class="eyebrow">MY COMPANION</div><h1>작은 실천을 먹고 자라는<br><span class="accent">{stage_name}</span></h1><p>습관 하나를 완료할 때마다 모리가 성장 포인트를 하나씩 얻어요.</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="character-stage"><div class="character-avatar">• ᴗ •</div></div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    left.metric("모리의 단계", f"Lv.{level}")
    right.metric("성장 포인트", f"{points}점")
    if level < 4:
        st.progress(min(points / next_goal, 1.0), text=f"다음 성장까지 {max(next_goal - points, 0)}점")
    else:
        st.progress(1.0, text="모리가 가장 빛나는 단계에 도달했어요")

    st.subheader("성장 배지")
    badges = [
        (1, "첫걸음", "첫 습관 완료"),
        (5, "다시 돌아옴", "누적 5회 완료"),
        (15, "꾸준한 동행", "누적 15회 완료"),
    ]
    columns = st.columns(3)
    for column, (threshold, title, description) in zip(columns, badges):
        unlocked = points >= threshold
        state_class = "" if unlocked else " locked"
        symbol = "★" if unlocked else "☆"
        column.markdown(
            f'<div class="badge-card{state_class}"><strong>{symbol} {title}</strong><p>{description}</p><small>{"획득했어요" if unlocked else f"{threshold - points}회 남았어요"}</small></div>',
            unsafe_allow_html=True,
        )

    st.info("추가 캐릭터와 특별 꾸미기 아이템은 구독 기능으로 확장할 예정이에요.")


def profile_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">MY PROFILE</div><h1>나에게 편안한 방식으로<br><span class="accent">멘토를 맞춰보세요.</span></h1><p>닉네임과 코칭 말투는 로그인한 모든 기기에 동기화돼요.</p></div>', unsafe_allow_html=True)

    with st.form("profile-settings"):
        nickname = st.text_input("닉네임", value=st.session_state.nickname, max_chars=20)
        selected_tone = st.selectbox(
            "코칭 말투",
            list(TONE_COPY),
            index=list(TONE_COPY).index(st.session_state.tone),
        )
        submitted = st.form_submit_button("프로필 저장", type="primary", use_container_width=True)
    if submitted:
        clean_nickname = nickname.strip()
        if not clean_nickname:
            st.warning("사용할 닉네임을 입력해주세요.")
        else:
            st.session_state.nickname = clean_nickname
            st.session_state.tone = selected_tone
            save_remote()
            st.success("프로필과 멘토 말투를 저장했어요.")
            st.rerun()

    title, subtitle = TONE_COPY[selected_tone]
    st.markdown(f'<div class="recommend-card"><div class="eyebrow">말투 미리보기</div><h3>{escape(title)}</h3><p>{escape(subtitle)}</p></div>', unsafe_allow_html=True)
    auth = st.session_state.auth or {}
    email = auth.get("user", {}).get("email")
    if email:
        st.caption(f"로그인 계정 · {email}")


def security_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">PRIVACY</div><h1>앱을 한 번 더<br><span class="accent">안전하게 잠그세요.</span></h1><p>로그인 비밀번호와 다른 4~6자리 숫자 PIN을 사용해요.</p></div>', unsafe_allow_html=True)

    if not st.session_state.app_lock:
        with st.form("set-app-lock"):
            pin = st.text_input("새 PIN", type="password", max_chars=6)
            confirmation = st.text_input("새 PIN 확인", type="password", max_chars=6)
            submitted = st.form_submit_button("앱 잠금 설정", type="primary", use_container_width=True)
        if submitted:
            if not pin.isdigit() or not 4 <= len(pin) <= 6:
                st.warning("PIN은 4~6자리 숫자로 입력해주세요.")
            elif pin != confirmation:
                st.warning("두 PIN이 일치하지 않아요.")
            else:
                salt = token_hex(16)
                st.session_state.app_lock = {"salt": salt, "digest": pin_digest(pin, salt)}
                st.session_state.app_unlocked = True
                save_remote()
                st.success("앱 잠금을 설정했어요.")
                st.rerun()
        return

    st.success("앱 잠금이 켜져 있어요. PIN 원문은 저장하지 않습니다.")
    if st.button("지금 잠그기", type="primary", use_container_width=True):
        st.session_state.app_unlocked = False
        st.rerun()

    with st.form("disable-app-lock"):
        current_pin = st.text_input("현재 PIN", type="password", max_chars=6)
        disable = st.form_submit_button("앱 잠금 끄기", use_container_width=True)
    if disable:
        if not valid_pin(current_pin):
            st.error("PIN이 올바르지 않아요.")
        else:
            st.session_state.app_lock = None
            st.session_state.app_unlocked = False
            save_remote()
            st.success("앱 잠금을 해제했어요.")
            st.rerun()


def habits_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">MY HABITS</div><h1>나에게 필요한 습관을<br><span class="accent">직접 만들어보세요.</span></h1><p>등록은 자유롭게, 오늘 집중할 습관은 최대 3개로 가볍게 유지해요.</p></div>', unsafe_allow_html=True)

    habits = all_habits()
    labels = {habit.key: f"{habit.icon} {habit.title}" for habit in habits}
    valid_focus = [key for key in st.session_state.focus_habits if key in labels]
    selected = st.multiselect(
        "오늘의 핵심 습관 (최대 3개)",
        options=list(labels),
        default=valid_focus,
        format_func=lambda key: labels[key],
        max_selections=3,
    )
    if st.button("핵심 습관 저장", type="primary"):
        st.session_state.focus_habits = selected
        record_today()
        save_remote()
        st.success("오늘의 핵심 습관을 저장했어요.")

    st.divider()
    st.subheader("새 습관 추가")
    with st.form("add-habit", clear_on_submit=True):
        title = st.text_input("습관 이름", placeholder="예: 부모님께 전화하기")
        category = st.selectbox("카테고리", ["운동", "공부", "독서", "수면", "식습관", "명상", "집안일", "관계", "기타"])
        default_minutes = st.number_input("기본 목표 시간", min_value=5, max_value=180, value=30, step=5)
        minimum_minutes = st.number_input("최소 목표 시간", min_value=1, max_value=30, value=5, step=1)
        submitted = st.form_submit_button("습관 추가", use_container_width=True)
    if submitted:
        clean_title = title.strip()
        if not clean_title:
            st.warning("습관 이름을 입력해주세요.")
        elif minimum_minutes > default_minutes:
            st.warning("최소 목표는 기본 목표보다 작아야 해요.")
        else:
            habit = Habit(
                key=f"custom-{uuid4().hex[:12]}",
                icon="○",
                category=category,
                title=clean_title,
                default_minutes=int(default_minutes),
                reduced_minutes=max(int(minimum_minutes), int(default_minutes) // 2),
                minimum_minutes=int(minimum_minutes),
            )
            st.session_state.custom_habits.append(habit_to_dict(habit))
            if len(st.session_state.focus_habits) < 3:
                st.session_state.focus_habits.append(habit.key)
            save_remote()
            st.success(f"'{clean_title}' 습관을 추가했어요.")
            st.rerun()

    if st.session_state.custom_habits:
        st.subheader("내가 만든 습관")
        for item in list(st.session_state.custom_habits):
            left, right = st.columns([5, 1])
            left.markdown(f"**{item['title']}** · {item['category']} · 기본 {item['default_minutes']}분 / 최소 {item['minimum_minutes']}분")
            if right.button("삭제", key=f"delete-{item['key']}"):
                st.session_state.custom_habits = [habit for habit in st.session_state.custom_habits if habit["key"] != item["key"]]
                st.session_state.focus_habits = [key for key in st.session_state.focus_habits if key != item["key"]]
                st.session_state.completed.discard(item["key"])
                st.session_state.accepted.pop(item["key"], None)
                save_remote()
                st.rerun()


initialize_state()
inject_styles()
backend = get_backend()
if backend and not st.session_state.auth:
    auth_screen(backend)
    st.stop()
load_remote()
if st.session_state.app_lock and not st.session_state.app_unlocked:
    lock_screen()
    st.stop()
sidebar()
if st.session_state.flash:
    st.toast(st.session_state.flash, icon="🌿")
    st.session_state.flash = ""

if st.session_state.page == "checkin":
    checkin_page()
elif st.session_state.page == "recommendation":
    recommendation_page()
elif st.session_state.page == "quick_adjust":
    quick_adjust_page()
elif st.session_state.page == "habits":
    habits_page()
elif st.session_state.page == "records":
    records_page()
elif st.session_state.page == "character":
    character_page()
elif st.session_state.page == "security":
    security_page()
elif st.session_state.page == "profile":
    profile_page()
else:
    today_page()
