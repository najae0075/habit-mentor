from pathlib import Path
from datetime import date, timedelta
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).parents[1] / "app.py"
STYLES = Path(__file__).parents[1] / "styles" / "app.css"
ADMIN_PAGE = Path(__file__).parents[1] / "pages" / "admin.py"


class DailyPaceTest(unittest.TestCase):
    def test_responsive_layout_covers_tablet_mobile_and_touch_targets(self):
        source = APP.read_text(encoding="utf-8")
        styles = STYLES.read_text(encoding="utf-8")
        self.assertIn('initial_sidebar_state="auto"', source)
        self.assertIn("(min-width:701px) and (max-width:1024px)", styles)
        self.assertIn("@media (max-width:700px)", styles)
        self.assertIn("flex-direction:column", styles)
        self.assertIn("min-height:46px", styles)
        self.assertIn('[data-testid="stDataFrame"]', styles)

    def test_admin_dashboard_avoids_altair_chart_dependency(self):
        source = ADMIN_PAGE.read_text(encoding="utf-8")
        self.assertNotIn("st.bar_chart(", source)
        self.assertIn("활성·체크인 사용자", source)
        self.assertIn("daily_rows", source)

    def test_admin_dashboard_supports_periods_and_conversions(self):
        source = ADMIN_PAGE.read_text(encoding="utf-8")
        for label in ("오늘", "최근 7일", "최근 30일"):
            self.assertIn(label, source)
        self.assertIn("checkin_completion_rate", source)
        self.assertIn("recommendation_completion_rate", source)
        self.assertIn("next_day_return_rate", source)

    def test_initial_screen_and_checkin_flow(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("오늘 체크인 시작" in button.label for button in app.button))

        next(button for button in app.button if "오늘 체크인 시작" in button.label).click()
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("나에게 맞는 목표 보기" in button.label for button in app.button))

    def test_core_journey_from_checkin_to_habit_completion(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)

        next(button for button in app.button if "오늘 체크인 시작" in button.label).click()
        app.run(timeout=15)
        # Streamlit 1.48 AppTest models segmented controls as a list-backed
        # button group even when the application uses single selection.
        for control in app.button_group:
            control.set_value([control.value])
        next(button for button in app.button if "나에게 맞는 목표 보기" in button.label).click()
        app.run(timeout=15)

        today_key = date.today().isoformat()
        self.assertEqual(app.session_state["page"], "recommendation")
        self.assertIn(today_key, app.session_state["checkin_dates"])
        self.assertIn(today_key, app.session_state["checkin_history"])

        selected_habit = app.session_state["selected_habit"]
        next(button for button in app.button if "이 목표로 할게요" in button.label).click()
        app.run(timeout=15)

        self.assertEqual(app.session_state["page"], "today")
        self.assertIn(selected_habit, app.session_state["accepted"])
        next(button for button in app.button if button.key == f"done-{selected_habit}").click()
        app.run(timeout=15)

        self.assertIn(selected_habit, app.session_state["completed"])
        self.assertIn(selected_habit, app.session_state["completion_history"][today_key])
        self.assertTrue(any(button.label == "완료 취소" for button in app.button))

        difficulty = next(radio for radio in app.radio if radio.label == "오늘 목표 난이도")
        difficulty.set_value("적당했어요")
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["feedback_history"][today_key][selected_habit],
            "적당했어요",
        )

    def test_recommendation_rule(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "recommendation"
        app.session_state["condition"] = "나쁨"
        app.session_state["overtime"] = "있어요"
        app.session_state["motivation"] = "낮음"
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("이 목표로 할게요" in button.label for button in app.button))

    def test_habit_management_page(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "habits"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.multiselect), 1)
        self.assertLessEqual(len(app.multiselect[0].value), 3)

    def test_records_page_shows_weekly_metrics(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "records"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 9)
        self.assertEqual(app.metric[0].label, "주간 성공률")
        self.assertTrue(any(metric.label == "평균 수면" for metric in app.metric))
        self.assertTrue(any(metric.label == "월간 완료" for metric in app.metric))
        self.assertTrue(any("이전 달" in button.label for button in app.button))
        self.assertTrue(any("다음 달" in button.label for button in app.button))

    def test_character_page_shows_growth(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "character"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 2)
        self.assertEqual(app.metric[0].label, "모리의 단계")
        self.assertEqual(app.metric[0].value, "Lv.1")
        self.assertEqual(app.metric[1].label, "성장 포인트")

    def test_app_lock_setup_and_locked_screen(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "security"
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.text_input), 2)

        app.session_state["app_lock"] = {"salt": "test", "digest": "invalid"}
        app.session_state["app_unlocked"] = False
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("잠금 해제" in button.label for button in app.button))

    def test_quick_adjust_offers_reduced_goal_and_rest(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "quick_adjust"
        app.session_state["selected_habit"] = "side_project"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertTrue(any("분으로 줄이기" in button.label for button in app.button))
        self.assertTrue(any("오늘은 회복하기" in button.label for button in app.button))

    def test_return_after_one_missed_day_preserves_streak(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        today = date.today()
        app.session_state["completion_history"] = {
            today.isoformat(): ["side_project"],
            (today - timedelta(days=2)).isoformat(): ["side_project"],
        }
        app.session_state["page"] = "records"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "2일")
        self.assertTrue(any("복귀 기회" in message.value for message in app.success))

    def test_profile_page_allows_nickname_and_tone_selection(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "profile"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertTrue(any(field.label == "닉네임" for field in app.text_input))
        self.assertTrue(any(field.label == "코칭 말투" for field in app.selectbox))
        self.assertTrue(any("프로필 저장" in button.label for button in app.button))

    def test_reminder_settings_include_single_retry_policy(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "reminders"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.time_input), 3)
        self.assertTrue(any("알림 설정 저장" in button.label for button in app.button))
        self.assertTrue(any("재알림 30분 뒤 1회" in message.value for message in app.info))

    def test_checkin_snapshot_produces_condition_insights(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["checkin_history"] = {
            date.today().isoformat(): {
                "condition": "나쁨",
                "overtime": "있어요",
                "available_minutes": 10,
                "motivation": "낮음",
                "sleep": 6.5,
                "note": "",
            }
        }
        app.session_state["page"] = "records"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["평균 수면"], "6.5시간")
        self.assertEqual(metrics["야근"], "1일")
        self.assertEqual(metrics["컨디션 나쁨"], "1일")

    def test_data_page_requires_explicit_reset_confirmation(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["page"] = "data"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertTrue(any("되돌릴 수 없음을 확인" in field.label for field in app.checkbox))
        self.assertTrue(any("기록 삭제" in field.label for field in app.text_input))
        self.assertTrue(any("활동 기록 초기화" in button.label for button in app.button))

    def test_new_user_onboarding_collects_core_preferences(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["auth"] = {
            "access_token": "test-token",
            "user": {"id": "test-user", "email": "new@example.com"},
        }
        app.session_state["onboarding_complete"] = False
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertTrue(any("어떻게 불러드릴까요" in field.label for field in app.text_input))
        self.assertTrue(any("어떤 멘토" in field.label for field in app.selectbox))
        self.assertEqual(len(app.multiselect), 1)
        self.assertTrue(any("설정 완료하고 시작하기" in button.label for button in app.button))

    def test_guest_preview_shows_storage_notice_and_signup_action(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["guest_mode"] = True
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertTrue(any("브라우저 세션" in message.value for message in app.info))
        signup = next(button for button in app.button if "가입하고 기록 저장하기" in button.label)
        signup.click()
        app.run(timeout=15)
        self.assertFalse(app.session_state["guest_mode"])

    def test_public_guide_explains_features_and_starts_preview(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        app.session_state["show_guide"] = True
        app.run(timeout=15)

        self.assertFalse(app.exception)
        markdown = " ".join(item.value for item in app.markdown)
        self.assertIn("오늘 상태 체크인", markdown)
        self.assertIn("유연한 목표 추천", markdown)
        self.assertIn("기록과 복귀 기회", markdown)
        self.assertIn("내 기록과 보안", markdown)
        preview = next(button for button in app.button if "체험 시작" in button.label)
        preview.click()
        app.run(timeout=15)
        self.assertTrue(app.session_state["guest_mode"])
        self.assertFalse(app.session_state["show_guide"])

    def test_difficult_feedback_reduces_next_recommendation(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        app.session_state["feedback_history"] = {yesterday: {"side_project": "버거웠어요"}}
        app.session_state["condition"] = "좋음"
        app.session_state["overtime"] = "없어요"
        app.session_state["motivation"] = "높음"
        app.session_state["available_minutes"] = 60
        app.session_state["selected_habit"] = "side_project"
        app.session_state["page"] = "recommendation"
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(app.slider[0].value, 20)


if __name__ == "__main__":
    unittest.main()
