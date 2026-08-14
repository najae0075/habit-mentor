import unittest

from state_validation import normalize_saved_state


class SavedStateValidationTest(unittest.TestCase):
    def test_non_dictionary_state_is_ignored(self):
        self.assertEqual(normalize_saved_state(None), {})
        self.assertEqual(normalize_saved_state(["invalid"]), {})

    def test_invalid_fields_are_dropped_or_reset_safely(self):
        normalized = normalize_saved_state(
            {
                "condition": "invalid",
                "focus_habits": "not-a-list",
                "completed": ["reading", 42],
                "custom_habits": [{"bad": True}],
                "app_lock": {"salt": "bad", "digest": "bad"},
                "reminder_settings": {
                    "enabled": "yes",
                    "moment": "invalid",
                    "morning_time": "99:99",
                },
            }
        )

        self.assertNotIn("condition", normalized)
        self.assertEqual(normalized["focus_habits"], [])
        self.assertEqual(normalized["completed"], ["reading"])
        self.assertEqual(normalized["custom_habits"], [])
        self.assertIsNone(normalized["app_lock"])
        self.assertFalse(normalized["reminder_settings"]["enabled"])
        self.assertEqual(normalized["reminder_settings"]["morning_time"], "08:00")

    def test_valid_state_is_preserved(self):
        custom_habit = {
            "key": "custom-reading",
            "icon": "book",
            "category": "독서",
            "title": "책 읽기",
            "default_minutes": 20,
            "reduced_minutes": 10,
            "minimum_minutes": 5,
        }
        saved = {
            "condition": "좋음",
            "available_minutes": 40,
            "completed": ["custom-reading"],
            "custom_habits": [custom_habit],
            "app_lock": {"salt": "00" * 16, "digest": "11" * 32},
            "reminder_settings": {
                "enabled": True,
                "moment": "퇴근 전",
                "departure_time": "17:30",
            },
        }

        normalized = normalize_saved_state(saved)
        self.assertEqual(normalized["condition"], "좋음")
        self.assertEqual(normalized["available_minutes"], 40)
        self.assertEqual(normalized["completed"], ["custom-reading"])
        self.assertEqual(normalized["custom_habits"], [custom_habit])
        self.assertEqual(normalized["app_lock"], saved["app_lock"])
        self.assertTrue(normalized["reminder_settings"]["enabled"])
        self.assertEqual(normalized["reminder_settings"]["departure_time"], "17:30")


if __name__ == "__main__":
    unittest.main()
