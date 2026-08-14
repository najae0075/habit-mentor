from pathlib import Path
from datetime import date, timedelta
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).parents[1] / "app.py"


class DailyPaceTest(unittest.TestCase):
    def test_initial_screen_and_checkin_flow(self):
        app = AppTest.from_file(str(APP)).run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("오늘 체크인 시작" in button.label for button in app.button))

        next(button for button in app.button if "오늘 체크인 시작" in button.label).click()
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(any("나에게 맞는 목표 보기" in button.label for button in app.button))

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
        self.assertEqual(len(app.metric), 3)
        self.assertEqual(app.metric[0].label, "주간 성공률")

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


if __name__ == "__main__":
    unittest.main()
