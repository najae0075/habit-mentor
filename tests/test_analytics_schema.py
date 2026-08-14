from pathlib import Path
import unittest


SCHEMA = Path(__file__).parents[1] / "supabase_schema.sql"
MIGRATION = Path(__file__).parents[1] / "supabase_migrations" / "20260815_upgrade_admin_analytics.sql"


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
            "checkin_completion_rate",
            "recommendation_completion_rate",
            "next_day_return_rate",
        ):
            self.assertIn(metric, sql)

    def test_admin_upgrade_migration_replaces_legacy_rpc_and_reloads_cache(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("drop function if exists public.admin_analytics_dashboard()", sql)
        self.assertIn("drop function if exists public.admin_analytics_dashboard(integer)", sql)
        self.assertIn("admin_analytics_dashboard(p_days integer default 7)", sql)
        self.assertIn("notify pgrst, 'reload schema'", sql)
        self.assertNotIn("drop table", sql)


if __name__ == "__main__":
    unittest.main()
