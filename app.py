from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from html import escape
from secrets import token_hex
from uuid import uuid4

import streamlit as st

from components.layout import inject_styles
from components.sidebar import render_sidebar
from pages.admin import admin_page
from pages.daily import (
    checkin_page as render_checkin_page,
    recommendation_page as render_recommendation_page,
    today_page as render_today_page,
)
from pages.guide import guide_screen
from pages.router import render_page
from services.supabase import SupabaseBackend, SupabaseError
from state_validation import normalize_saved_state
from domain.habits import DEFAULT_HABITS as HABITS, Habit, build_habits, habit_to_dict, select_focused
from domain.progress import (
    calendar_summary as calculate_calendar_summary,
    offset_month as calculate_offset_month,
    streak_details as calculate_streak_details,
    weekly_stats as calculate_weekly_stats,
)
from domain.recommendations import recommend_habit


st.set_page_config(
    page_title="데일리 페이스",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="auto",
)


def all_habits() -> list[Habit]:
    return build_habits(st.session_state.custom_habits)


def focused_habits() -> list[Habit]:
    return select_focused(all_habits(), st.session_state.focus_habits)

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
        "checkin_history": {},
        "active_date": date.today().isoformat(),
        "adjustment_history": {},
        "rest_history": {},
        "feedback_history": {},
        "reminder_settings": {
            "enabled": False,
            "moment": "아침",
            "morning_time": "08:00",
            "departure_time": "18:00",
            "habit_time": "20:00",
        },
        "reminder_history": {},
        "app_lock": None,
        "app_unlocked": False,
        "calendar_offset": 0,
        "onboarding_complete": True,
        "accepted": {},
        "custom_habits": [],
        "focus_habits": [habit.key for habit in HABITS],
        "flash": "",
        "auth": None,
        "guest_mode": False,
        "show_guide": False,
        "admin_metrics": None,
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


def is_admin() -> bool:
    auth = st.session_state.auth or {}
    user_id = auth.get("user", {}).get("id", "")
    if not user_id:
        return False
    try:
        configured = st.secrets.get("ADMIN_USER_IDS", "")
    except FileNotFoundError:
        return False
    if isinstance(configured, str):
        admin_ids = {item.strip() for item in configured.split(",") if item.strip()}
    elif isinstance(configured, (list, tuple, set)):
        admin_ids = {str(item).strip() for item in configured}
    else:
        admin_ids = set()
    return user_id in admin_ids


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
        "checkin_history": st.session_state.checkin_history,
        "active_date": st.session_state.active_date,
        "adjustment_history": st.session_state.adjustment_history,
        "rest_history": st.session_state.rest_history,
        "feedback_history": st.session_state.feedback_history,
        "reminder_settings": st.session_state.reminder_settings,
        "reminder_history": st.session_state.reminder_history,
        "app_lock": st.session_state.app_lock,
        "onboarding_complete": st.session_state.onboarding_complete,
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


def track_event(
    event_name: str,
    metadata: dict[str, object] | None = None,
    event_key: str | None = None,
) -> None:
    """Record privacy-safe usage data without interrupting the user flow."""
    backend = get_backend()
    auth = st.session_state.auth
    if not backend or not auth:
        return
    try:
        backend.track_event(
            auth["user"]["id"], auth["access_token"], event_name, metadata, event_key
        )
    except (SupabaseError, KeyError, TypeError):
        return


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
    normalized = normalize_saved_state(saved)
    if saved:
        for key in ("condition", "overtime", "available_minutes", "motivation", "sleep", "note", "tone", "nickname", "accepted", "custom_habits", "focus_habits", "completion_history", "focus_history", "checkin_dates", "checkin_history", "active_date", "adjustment_history", "rest_history", "feedback_history", "reminder_settings", "reminder_history", "app_lock", "onboarding_complete"):
            if key in normalized:
                st.session_state[key] = normalized[key]
        st.session_state.completed = set(normalized.get("completed", []))
        if "onboarding_complete" not in normalized:
            st.session_state.onboarding_complete = True
    else:
        st.session_state.onboarding_complete = False
    today_key = date.today().isoformat()
    if st.session_state.active_date != today_key:
        st.session_state.completed = set(st.session_state.completion_history.get(today_key, []))
        st.session_state.active_date = today_key
    st.session_state.remote_loaded = True
    track_event("daily_active", event_key=f"daily_active:{today_key}")
    previous_dates = sorted(day for day in st.session_state.checkin_dates if day < today_key)
    if previous_dates:
        try:
            days_since_last = (date.fromisoformat(today_key) - date.fromisoformat(previous_dates[-1])).days
        except ValueError:
            days_since_last = 0
        if days_since_last > 0:
            track_event(
                "user_returned",
                {"days_since_last_checkin": days_since_last},
                event_key=f"user_returned:{today_key}",
            )


def record_today() -> None:
    today_key = date.today().isoformat()
    st.session_state.active_date = today_key
    st.session_state.completion_history[today_key] = sorted(st.session_state.completed)
    st.session_state.focus_history[today_key] = list(st.session_state.focus_habits)


def weekly_stats() -> tuple[int, int, int]:
    return calculate_weekly_stats(
        st.session_state.focus_history,
        st.session_state.completion_history,
        st.session_state.rest_history,
        st.session_state.checkin_dates,
    )


def weekly_checkin_insights() -> tuple[float | None, int, int]:
    today = date.today()
    dates = {(today - timedelta(days=offset)).isoformat() for offset in range(7)}
    entries = [entry for day, entry in st.session_state.checkin_history.items() if day in dates]
    sleep_values = [float(entry["sleep"]) for entry in entries if isinstance(entry.get("sleep"), (int, float))]
    average_sleep = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else None
    overtime_days = sum(entry.get("overtime") == "있어요" for entry in entries)
    low_condition_days = sum(entry.get("condition") == "나쁨" for entry in entries)
    return average_sleep, overtime_days, low_condition_days


def streak_details() -> tuple[int, str | None]:
    return calculate_streak_details(st.session_state.completion_history, st.session_state.rest_history)


def offset_month(offset: int) -> tuple[int, int]:
    return calculate_offset_month(offset)


def calendar_summary(year: int, month: int) -> tuple[int, int, int]:
    return calculate_calendar_summary(
        st.session_state.completion_history,
        st.session_state.rest_history,
        st.session_state.checkin_dates,
        year,
        month,
    )


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


def exportable_data() -> dict[str, object]:
    return {
        "exported_at": now_kst().isoformat(),
        "profile": {"nickname": st.session_state.nickname, "tone": st.session_state.tone},
        "habits": {
            "custom": st.session_state.custom_habits,
            "focused": st.session_state.focus_habits,
            "accepted_minutes": st.session_state.accepted,
        },
        "activity": {
            "completion_history": st.session_state.completion_history,
            "focus_history": st.session_state.focus_history,
            "checkin_history": st.session_state.checkin_history,
            "adjustment_history": st.session_state.adjustment_history,
            "rest_history": st.session_state.rest_history,
            "feedback_history": st.session_state.feedback_history,
        },
        "reminder_settings": st.session_state.reminder_settings,
    }


def clear_activity_data() -> None:
    st.session_state.completed = set()
    st.session_state.completion_history = {}
    st.session_state.focus_history = {}
    st.session_state.checkin_dates = []
    st.session_state.checkin_history = {}
    st.session_state.adjustment_history = {}
    st.session_state.rest_history = {}
    st.session_state.feedback_history = {}
    st.session_state.reminder_history = {}
    st.session_state.active_date = date.today().isoformat()


def now_kst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def reminder_due_at(now: datetime) -> datetime:
    settings = st.session_state.reminder_settings
    moment = settings.get("moment", "아침")
    field = {"아침": "morning_time", "퇴근 전": "departure_time", "습관 시작 전": "habit_time"}[moment]
    hour, minute = (int(part) for part in settings.get(field, "08:00").split(":"))
    due = datetime.combine(now.date(), time(hour, minute), tzinfo=now.tzinfo)
    if moment == "퇴근 전":
        due -= timedelta(minutes=30)
    elif moment == "습관 시작 전":
        due -= timedelta(minutes=10)
    return due


def render_due_reminder() -> None:
    settings = st.session_state.reminder_settings
    if not settings.get("enabled"):
        return
    now = now_kst()
    today_key = now.date().isoformat()
    if today_key in st.session_state.checkin_dates:
        return
    history = st.session_state.reminder_history
    state = history.get(today_key)
    phase = None
    if state is None and now >= reminder_due_at(now):
        phase = "first"
        history[today_key] = {"phase": phase, "shown_at": now.isoformat(), "resolved": False}
        save_remote()
    elif state and not state.get("resolved") and state.get("phase") == "first":
        retry_at = datetime.fromisoformat(state["shown_at"]) + timedelta(minutes=30)
        if now >= retry_at:
            phase = "retry"
            state["phase"] = phase
            state["shown_at"] = now.isoformat()
            save_remote()
    if phase is None:
        return

    track_event(
        "reminder_shown",
        {"phase": phase},
        event_key=f"reminder_shown:{today_key}:{phase}",
    )

    label = "부드러운 재알림" if phase == "retry" else "오늘의 체크인"
    st.info(f"♡ {label} · 지금 컨디션을 알려주면 오늘에 맞는 목표를 제안할게요.")
    check_col, later_col, dismiss_col = st.columns(3)
    if check_col.button("지금 체크인", type="primary", key=f"reminder-check-{phase}", use_container_width=True):
        history[today_key]["resolved"] = True
        save_remote()
        track_event("reminder_acknowledged", {"phase": phase, "action": "checkin"})
        go("checkin")
    if phase == "first" and later_col.button("30분 뒤 다시", key="reminder-later", use_container_width=True):
        history[today_key]["shown_at"] = now.isoformat()
        save_remote()
        track_event("reminder_acknowledged", {"phase": phase, "action": "later"})
        st.rerun()
    if dismiss_col.button("오늘은 괜찮아요", key=f"reminder-dismiss-{phase}", use_container_width=True):
        history[today_key]["resolved"] = True
        save_remote()
        track_event("reminder_acknowledged", {"phase": phase, "action": "dismiss"})
        st.rerun()


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
                st.session_state.guest_mode = False
                st.session_state.admin_metrics = None
                st.session_state.remote_loaded = False
                st.rerun()
            else:
                st.success("확인 이메일을 보냈어요. 이메일 인증 후 로그인해주세요.")

        st.divider()
        if st.button("앱 사용방법 보기", use_container_width=True):
            st.session_state.show_guide = True
            st.rerun()
        st.caption("가입 전에 체크인과 맞춤 목표 추천 흐름을 먼저 경험해보세요.")
        if st.button("회원가입 없이 체험하기", use_container_width=True):
            st.session_state.guest_mode = True
            st.session_state.show_guide = False
            st.session_state.nickname = "체험 사용자"
            st.session_state.page = "today"
            st.session_state.onboarding_complete = True
            st.rerun()


def onboarding_screen() -> None:
    auth = st.session_state.auth or {}
    email = auth.get("user", {}).get("email", "")
    suggested_name = email.split("@", 1)[0] if email else ""
    st.markdown('<div class="center-heading"><div class="eyebrow">WELCOME TO DAILY PACE</div><h1>완벽한 계획보다<br><span class="accent">나에게 맞는 시작.</span></h1><p>처음 한 번만 알려주시면 오늘부터 편안하게 함께할게요.</p></div>', unsafe_allow_html=True)
    habit_labels = {habit.key: f"{habit.icon} {habit.title}" for habit in HABITS}
    with st.form("onboarding"):
        nickname = st.text_input("어떻게 불러드릴까요?", value=suggested_name, max_chars=20)
        tone = st.selectbox("어떤 멘토와 함께할까요?", list(TONE_COPY))
        focus = st.multiselect(
            "먼저 집중할 핵심 습관 (최대 3개)",
            options=list(habit_labels),
            default=[habit.key for habit in HABITS],
            format_func=lambda key: habit_labels[key],
            max_selections=3,
        )
        reminder_enabled = st.toggle("아침 체크인 알림 받기")
        morning_time = st.time_input("아침 체크인 시간", value=time(8, 0))
        submitted = st.form_submit_button("설정 완료하고 시작하기", type="primary", use_container_width=True)
    if submitted:
        clean_name = nickname.strip()
        if not clean_name:
            st.warning("사용할 닉네임을 입력해주세요.")
        elif not focus:
            st.warning("핵심 습관을 하나 이상 선택해주세요.")
        else:
            st.session_state.nickname = clean_name
            st.session_state.tone = tone
            st.session_state.focus_habits = focus
            st.session_state.reminder_settings = {
                **st.session_state.reminder_settings,
                "enabled": reminder_enabled,
                "moment": "아침",
                "morning_time": morning_time.strftime("%H:%M"),
            }
            st.session_state.onboarding_complete = True
            record_today()
            save_remote()
            track_event(
                "onboarding_completed",
                {"focus_habit_count": len(focus), "reminder_enabled": reminder_enabled},
                event_key="onboarding_completed",
            )
            st.session_state.flash = f"{clean_name}님, 데일리 페이스에 오신 걸 환영해요."
            st.rerun()


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


def latest_habit_feedback(habit_key: str) -> str | None:
    for day in sorted(st.session_state.feedback_history, reverse=True):
        feedback = st.session_state.feedback_history.get(day, {}).get(habit_key)
        if feedback:
            return feedback
    return None


def recommend(habit: Habit) -> dict[str, object]:
    return recommend_habit(
        habit,
        condition=st.session_state.condition,
        has_overtime=st.session_state.overtime == "있어요",
        motivation=st.session_state.motivation,
        sleep_hours=st.session_state.sleep,
        available_minutes=st.session_state.available_minutes,
        recent_feedback=latest_habit_feedback(habit.key),
    )



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
        track_event(
            "goal_reduced",
            {"habit_key": habit.key, "reason": reason, "minutes": habit.minimum_minutes},
        )
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
        track_event("rest_selected", {"habit_key": habit.key, "reason": reason})
        st.session_state.flash = "휴식을 오늘의 목표로 정했어요. 회복도 꾸준함의 일부예요."
        go("today")


def monthly_calendar() -> None:
    previous, heading, following = st.columns([1, 3, 1])
    if previous.button("← 이전 달", use_container_width=True):
        st.session_state.calendar_offset -= 1
        st.rerun()
    year, month = offset_month(st.session_state.calendar_offset)
    heading.markdown(f"<h3 style='text-align:center'>{year}년 {month}월</h3>", unsafe_allow_html=True)
    if following.button("다음 달 →", use_container_width=True):
        st.session_state.calendar_offset += 1
        st.rerun()

    completed_count, rest_days, checkins = calendar_summary(year, month)
    col1, col2, col3 = st.columns(3)
    col1.metric("월간 완료", f"{completed_count}회")
    col2.metric("회복일", f"{rest_days}일")
    col3.metric("체크인", f"{checkins}일")

    first_weekday, days_in_month = monthrange(year, month)
    cells = [f'<div class="calendar-head">{label}</div>' for label in ("월", "화", "수", "목", "금", "토", "일")]
    cells.extend('<div class="calendar-day empty"></div>' for _ in range(first_weekday))
    for day_number in range(1, days_in_month + 1):
        day_key = f"{year:04d}-{month:02d}-{day_number:02d}"
        completed = len(set(st.session_state.completion_history.get(day_key, [])))
        rested = bool(st.session_state.rest_history.get(day_key, []))
        checked = day_key in st.session_state.checkin_dates
        classes = ["calendar-day"]
        if completed:
            classes.append("completed")
        if rested:
            classes.append("recovery")
        if checked:
            classes.append("checked")
        details = []
        if completed:
            details.append(f"✓ {completed}개")
        if rested:
            details.append("♡ 회복")
        if checked and not details:
            details.append("· 체크인")
        cells.append(f'<div class="{" ".join(classes)}"><strong>{day_number}</strong>{"<br>".join(details)}</div>')
    st.markdown(f'<div class="calendar-grid">{"".join(cells)}</div>', unsafe_allow_html=True)
    st.caption("초록색은 습관 완료, 살구색은 계획한 회복, 아래 선은 체크인을 뜻해요.")


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

    st.subheader("최근 컨디션 인사이트")
    average_sleep, overtime_days, low_condition_days = weekly_checkin_insights()
    insight1, insight2, insight3 = st.columns(3)
    insight1.metric("평균 수면", f"{average_sleep:.1f}시간" if average_sleep is not None else "기록 없음")
    insight2.metric("야근", f"{overtime_days}일")
    insight3.metric("컨디션 나쁨", f"{low_condition_days}일")
    if average_sleep is not None and average_sleep < 6:
        st.warning("최근 수면이 부족한 편이에요. 오늘은 최소 목표나 회복 목표를 우선해보세요.")
    elif overtime_days >= 3:
        st.info("야근이 잦았어요. 이번 주 목표를 평소보다 작게 유지해도 충분해요.")
    elif average_sleep is not None:
        st.success("체크인 데이터가 쌓이고 있어요. 내 리듬을 알아가는 것도 중요한 진전이에요.")

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

    st.divider()
    st.subheader("월간 캘린더")
    monthly_calendar()


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


def reminders_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">CHECK-IN REMINDER</div><h1>재촉하지 않고<br><span class="accent">한 번만 다정하게.</span></h1><p>원하는 시점에 체크인을 안내하고, 놓치면 30분 뒤 한 번만 다시 알려드려요.</p></div>', unsafe_allow_html=True)
    settings = st.session_state.reminder_settings
    with st.form("reminder-settings"):
        enabled = st.toggle("체크인 알림 사용", value=settings.get("enabled", False))
        moment = st.segmented_control(
            "알림 시점",
            ["아침", "퇴근 전", "습관 시작 전"],
            default=settings.get("moment", "아침"),
        )
        morning = st.time_input("아침 시간", value=time.fromisoformat(settings.get("morning_time", "08:00")))
        departure = st.time_input("예상 퇴근 시간", value=time.fromisoformat(settings.get("departure_time", "18:00")))
        habit_start = st.time_input("습관 시작 시간", value=time.fromisoformat(settings.get("habit_time", "20:00")))
        submitted = st.form_submit_button("알림 설정 저장", type="primary", use_container_width=True)
    if submitted:
        st.session_state.reminder_settings = {
            "enabled": enabled,
            "moment": moment,
            "morning_time": morning.strftime("%H:%M"),
            "departure_time": departure.strftime("%H:%M"),
            "habit_time": habit_start.strftime("%H:%M"),
        }
        save_remote()
        st.success("알림 설정을 저장했어요.")
        st.rerun()

    selected_time = {
        "아침": settings.get("morning_time", "08:00"),
        "퇴근 전": f"{settings.get('departure_time', '18:00')} 30분 전",
        "습관 시작 전": f"{settings.get('habit_time', '20:00')} 10분 전",
    }[settings.get("moment", "아침")]
    st.info(f"현재 설정 · {settings.get('moment', '아침')} {selected_time} · 재알림 30분 뒤 1회")
    st.caption("현재 버전은 앱을 열어두거나 다시 방문했을 때 표시되는 앱 내부 알림입니다. 브라우저 푸시 알림은 다음 단계에서 연결할 수 있어요.")


def data_page() -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown('<div class="center-heading"><div class="eyebrow">MY DATA</div><h1>내 기록의 주인은<br><span class="accent">언제나 나예요.</span></h1><p>저장된 데이터를 내려받거나 활동 기록을 초기화할 수 있어요.</p></div>', unsafe_allow_html=True)

    payload = json.dumps(exportable_data(), ensure_ascii=False, indent=2)
    st.subheader("데이터 내보내기")
    st.write("프로필, 습관 설정, 체크인과 완료 기록을 JSON 파일로 내려받습니다.")
    st.download_button(
        "내 데이터 다운로드",
        data=payload,
        file_name=f"daily-pace-{date.today().isoformat()}.json",
        mime="application/json",
        type="primary",
        use_container_width=True,
    )
    st.caption("보안을 위해 앱 잠금 PIN 해시는 내보내기에 포함하지 않습니다.")

    st.divider()
    st.subheader("활동 기록 초기화")
    st.warning("완료·체크인·회복·재조정 기록과 캐릭터 성장이 초기화됩니다. 계정, 닉네임, 습관 목록과 앱 잠금은 유지됩니다.")
    with st.form("clear-activity-data"):
        confirmed = st.checkbox("초기화 후 되돌릴 수 없음을 확인했습니다.")
        phrase = st.text_input("확인을 위해 ‘기록 삭제’를 입력해주세요.")
        clear = st.form_submit_button("활동 기록 초기화", use_container_width=True)
    if clear:
        if not confirmed or phrase.strip() != "기록 삭제":
            st.error("확인 항목을 선택하고 ‘기록 삭제’를 정확히 입력해주세요.")
        else:
            clear_activity_data()
            save_remote()
            st.session_state.flash = "활동 기록을 초기화했어요. 새로운 시작도 온전한 선택이에요."
            go("today")


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
if not st.session_state.auth and not st.session_state.guest_mode and st.session_state.show_guide:
    guide_screen()
    st.stop()
if backend and not st.session_state.auth and not st.session_state.guest_mode:
    auth_screen(backend)
    st.stop()
load_remote()
if st.session_state.auth and not st.session_state.onboarding_complete:
    onboarding_screen()
    st.stop()
if st.session_state.app_lock and not st.session_state.app_unlocked:
    lock_screen()
    st.stop()
render_sidebar(go, is_admin, display_name)
render_due_reminder()
if st.session_state.flash:
    st.toast(st.session_state.flash, icon="🌿")
    st.session_state.flash = ""

daily_page_dependencies = {
    "display_name": display_name,
    "focused_habits": focused_habits,
    "weekly_stats": weekly_stats,
    "streak_details": streak_details,
    "record_today": record_today,
    "save_remote": save_remote,
    "track_event": track_event,
    "go": go,
}

render_page(
    st.session_state.page,
    {
        "checkin": lambda: render_checkin_page(
            focused_habits=focused_habits,
            save_remote=save_remote,
            track_event=track_event,
            go=go,
        ),
        "recommendation": lambda: render_recommendation_page(
            all_habits=all_habits,
            recommend=recommend,
            save_remote=save_remote,
            track_event=track_event,
            go=go,
            tone_copy=TONE_COPY,
        ),
        "quick_adjust": quick_adjust_page,
        "habits": habits_page,
        "records": records_page,
        "character": character_page,
        "security": security_page,
        "profile": profile_page,
        "reminders": reminders_page,
        "data": data_page,
        "admin": lambda: admin_page(go, is_admin, get_backend, SupabaseError),
    },
    lambda: render_today_page(**daily_page_dependencies),
)
