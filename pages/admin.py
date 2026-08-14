"""Administrator analytics screen."""

import streamlit as st


def admin_page(go, is_admin, get_backend, supabase_error) -> None:
    if st.button("← 오늘로 돌아가기"):
        go("today")
    st.markdown(
        '<div class="center-heading"><div class="eyebrow">OPERATIONS</div>'
        '<h1>사용자가 다시 돌아오는지<br><span class="accent">숫자로 확인해요.</span></h1>'
        '<p>한국 시간 기준의 서비스 핵심 지표입니다. 개인의 자유 입력 내용은 표시하지 않아요.</p></div>',
        unsafe_allow_html=True,
    )
    if not is_admin():
        st.error("운영 지표를 볼 수 있는 관리자 계정이 아닙니다.")
        return

    backend = get_backend()
    auth = st.session_state.auth
    if not backend or not auth:
        st.error("운영 지표를 불러오려면 관리자 계정으로 로그인해주세요.")
        return

    period_label = st.segmented_control(
        "조회 기간",
        ["오늘", "최근 7일", "최근 30일"],
        default="최근 7일",
    )
    period_days = {"오늘": 1, "최근 7일": 7, "최근 30일": 30}[period_label]
    refresh = st.button("지표 새로고침", type="primary")
    cached = st.session_state.admin_metrics
    if refresh or not isinstance(cached, dict) or cached.get("_period_days") != period_days:
        try:
            loaded = backend.load_admin_metrics(auth["access_token"], period_days)
            st.session_state.admin_metrics = {**loaded, "_period_days": period_days}
        except (supabase_error, KeyError, TypeError) as error:
            st.error(f"운영 지표를 불러오지 못했습니다: {error}")
            return

    metrics = st.session_state.admin_metrics or {}
    if metrics.get("_legacy_rpc"):
        st.warning(
            "Supabase의 이전 집계 함수를 사용 중이에요. 페이지는 계속 사용할 수 있지만 기간별 지표와 전환율을 적용하려면 최신 supabase_schema.sql을 실행해주세요."
        )
    top = st.columns(4)
    top[0].metric("가입 사용자", f"{metrics.get('registered_users', 0):,}명")
    top[1].metric(f"{period_label} 활성 사용자", f"{metrics.get('active_users', 0):,}명")
    top[2].metric(f"{period_label} 체크인율", f"{metrics.get('checkin_rate') or 0}%")
    top[3].metric("다음 날 복귀", f"{metrics.get('next_day_returns', 0):,}명")

    retention = st.columns(2)
    retention[0].metric("7일 유지율", f"{metrics.get('retention_7') or 0}%")
    retention[1].metric("30일 유지율", f"{metrics.get('retention_30') or 0}%")
    st.caption("유지율은 가입일로부터 정확히 7일 또는 30일째 앱을 다시 사용한 사용자 비율입니다.")

    conversion = st.columns(3)
    conversion[0].metric("체크인 시작 → 완료", f"{metrics.get('checkin_completion_rate') or 0}%")
    conversion[1].metric("추천 수락 → 습관 완료", f"{metrics.get('recommendation_completion_rate') or 0}%")
    conversion[2].metric("다음 날 복귀율", f"{metrics.get('next_day_return_rate') or 0}%")

    st.subheader(f"{period_label} 핵심 행동")
    funnel = [
        {"지표": "체크인 시작", "값": metrics.get("checkin_started_users", 0)},
        {"지표": "체크인 완료", "값": metrics.get("checkin_completed_users", 0)},
        {"지표": "추천 수락", "값": metrics.get("recommendations_accepted", 0)},
        {"지표": "추천 수정", "값": metrics.get("recommendations_modified", 0)},
        {"지표": "습관 완료", "값": metrics.get("habits_completed", 0)},
        {"지표": "알림 노출", "값": metrics.get("reminders_shown", 0)},
        {"지표": "알림 확인", "값": metrics.get("reminders_acknowledged", 0)},
    ]
    st.dataframe(funnel, hide_index=True, use_container_width=True)

    daily = metrics.get("daily", [])
    if daily:
        st.subheader(f"{period_label} 활성·체크인 사용자")
        daily_rows = [
            {
                "날짜": row.get("day", ""),
                "활성 사용자": row.get("active_users", 0),
                "체크인 사용자": row.get("checked_in_users", 0),
            }
            for row in daily
            if isinstance(row, dict)
        ]
        st.dataframe(daily_rows, hide_index=True, use_container_width=True)
        st.caption("한국 시간 기준 일별 수치이며 외부 차트 라이브러리 없이 표시합니다.")
    else:
        st.info("아직 표시할 일별 이벤트가 없습니다.")
