from pathlib import Path
import unittest


SCHEMA = Path(__file__).parents[1] / "supabase_schema.sql"


class AnalyticsSchemaTest(unittest.TestCase):
    def test_admin_metrics_are_protected_and_cover_core_metrics(self):
        sql = SCHEMA.read_text(encoding="utf-8")

        self.assertIn("security definer", sql.lower())
        self.assertIn("public.admin_users", sql)
        self.assertIn("administrator access required", sql)
        for metric in (
            "registered_users",
            "active_users",
            "checkin_rate",
            "recommendations_modified",
            "reminders_acknowledged",
            "next_day_returns",
            "retention_7",
            "retention_30",
        ):
            self.assertIn(metric, sql)


if __name__ == "__main__":
    unittest.main()
