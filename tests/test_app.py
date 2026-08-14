from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
