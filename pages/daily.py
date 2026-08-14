"""Today, check-in, and recommendation screens."""

from datetime import date
from html import escape

import streamlit as st


def today_page(*, display_name, focused_habits, weekly_stats, streak_details, record_today, save_remote, track_event, go) -> None:
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
        track_event("checkin_started", event_key=f"checkin_started:{date.today().isoformat()}")
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
                    track_event("habit_completion_undone", {"habit_key": habit.key})
                else:
                    st.session_state.completed.add(habit.key)
                    track_event("habit_completed", {"habit_key": habit.key})
                    if habit.key in rested_today:
                        st.session_state.rest_history[today_key] = [key for key in rested_today if key != habit.key]
                record_today()
                save_remote()
                st.rerun()
            if done:
                existing_feedback = st.session_state.feedback_history.get(today_key, {}).get(habit.key)
                options = ["쉬웠어요", "적당했어요", "버거웠어요"]
                feedback = st.radio(
                    "오늘 목표 난이도",
                    options,
                    index=options.index(existing_feedback) if existing_feedback in options else None,
                    horizontal=True,
                    key=f"feedback-{today_key}-{habit.key}",
                )
                if feedback and feedback != existing_feedback:
                    st.session_state.feedback_history.setdefault(today_key, {})[habit.key] = feedback
                    save_remote()
                    st.toast("다음 목표 추천에 반영할게요.")
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


def checkin_page(*, focused_habits, save_remote, track_event, go) -> None:
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
            st.session_state.checkin_history[today_key] = {
                "condition": st.session_state.condition,
                "overtime": st.session_state.overtime,
                "available_minutes": st.session_state.available_minutes,
                "motivation": st.session_state.motivation,
                "sleep": st.session_state.sleep,
                "note": st.session_state.note,
            }
            save_remote()
            track_event(
                "checkin_completed",
                {"focus_habit_count": len(daily_habits)},
                event_key=f"checkin_completed:{today_key}",
            )
            go("recommendation")


def recommendation_page(*, all_habits, recommend, save_remote, track_event, go, tone_copy) -> None:
    habit = next((h for h in all_habits() if h.key == st.session_state.selected_habit), None)
    if habit is None:
        st.warning("추천할 습관이 없습니다. 먼저 핵심 습관을 선택해주세요.")
        if st.button("습관 선택하기"):
            go("habits")
        return
    suggestion = recommend(habit)
    if st.button("← 체크인 수정하기"):
        go("checkin")
    title, subtitle = tone_copy[st.session_state.tone]
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
            track_event(
                "recommendation_accepted",
                {
                    "habit_key": habit.key,
                    "recommended_minutes": suggestion["minutes"],
                    "accepted_minutes": custom,
                    "modified": custom != suggestion["minutes"],
                    "level": suggestion["level"],
                },
            )
            go("today")
    st.markdown('<div class="recovery">♡ 하루 쉬어도 기록은 사라지지 않아요. 내일 돌아오면 연속 기록을 이어드릴게요.</div>', unsafe_allow_html=True)
