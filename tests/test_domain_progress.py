from datetime import date

from domain.progress import calendar_summary, character_progress, offset_month, streak_details, weekly_stats


def test_weekly_stats_uses_focus_and_ignores_planned_rest():
    focus = {"2026-08-15": ["read", "walk"], "2026-08-14": ["read"]}
    completed = {"2026-08-15": ["read"], "2026-08-14": ["read"]}
    rest = {"2026-08-15": ["walk"]}

    assert weekly_stats(focus, completed, rest, ["2026-08-14", "2026-08-15"], today=date(2026, 8, 15)) == (100, 2, 2)


def test_streak_allows_one_recovery_gap():
    completed = {"2026-08-15": ["read"], "2026-08-13": ["read"], "2026-08-12": ["read"]}

    assert streak_details(completed, {}, today=date(2026, 8, 15)) == (3, "2026-08-14")


def test_calendar_and_character_progress_are_pure_calculations():
    completed = {"2026-08-01": ["read", "read", "walk"], "2026-08-02": ["read"], "2026-07-31": ["walk"]}
    rest = {"2026-08-03": ["read"]}

    assert calendar_summary(completed, rest, ["2026-08-01", "2026-08-03"], 2026, 8) == (3, 1, 2)
    assert character_progress(completed) == (4, 1, 5)
    assert offset_month(1, today=date(2026, 12, 10)) == (2027, 1)
