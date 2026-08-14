"""Pure progress, streak, and calendar calculations."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping, Sequence


History = Mapping[str, Sequence[str]]


def streak_details(
    completion_history: History,
    rest_history: History,
    *,
    today: date | None = None,
) -> tuple[int, str | None]:
    cursor = today or date.today()
    today_key = cursor.isoformat()
    if not completion_history.get(today_key) and not rest_history.get(today_key):
        cursor -= timedelta(days=1)

    streak = 0
    recovery_day = None
    recovery_candidate = None
    for _ in range(366):
        day_key = cursor.isoformat()
        completed = bool(completion_history.get(day_key))
        planned_rest = bool(rest_history.get(day_key))
        if completed or planned_rest:
            streak += 1
            if recovery_candidate:
                recovery_day = recovery_candidate
                recovery_candidate = None
        elif streak and recovery_day is None and recovery_candidate is None:
            recovery_candidate = day_key
        else:
            break
        cursor -= timedelta(days=1)
    return streak, recovery_day


def weekly_stats(
    focus_history: History,
    completion_history: History,
    rest_history: History,
    checkin_dates: Sequence[str],
    *,
    today: date | None = None,
) -> tuple[int, int, int]:
    current = today or date.today()
    dates = [(current - timedelta(days=offset)).isoformat() for offset in range(7)]
    completed_count = 0
    target_count = 0
    for day in dates:
        focus = set(focus_history.get(day, [])) - set(rest_history.get(day, []))
        completed = set(completion_history.get(day, []))
        completed_count += len(completed & focus)
        target_count += len(focus)
    success_rate = round(completed_count / target_count * 100) if target_count else 0
    streak, _ = streak_details(completion_history, rest_history, today=current)
    return success_rate, streak, len(set(checkin_dates) & set(dates))


def calendar_summary(
    completion_history: History,
    rest_history: History,
    checkin_dates: Sequence[str],
    year: int,
    month: int,
) -> tuple[int, int, int]:
    prefix = f"{year:04d}-{month:02d}-"
    completions = sum(len(set(items)) for day, items in completion_history.items() if day.startswith(prefix))
    rest_days = sum(bool(items) for day, items in rest_history.items() if day.startswith(prefix))
    checkins = sum(day.startswith(prefix) for day in set(checkin_dates))
    return completions, rest_days, checkins


def offset_month(offset: int, *, today: date | None = None) -> tuple[int, int]:
    current = today or date.today()
    month_index = current.year * 12 + current.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return year, zero_based_month + 1


def character_progress(completion_history: History) -> tuple[int, int, int]:
    points = sum(len(set(items)) for items in completion_history.values())
    thresholds = (0, 5, 15, 30)
    level = max(index + 1 for index, threshold in enumerate(thresholds) if points >= threshold)
    next_goal = thresholds[level] if level < len(thresholds) else thresholds[-1]
    return points, level, next_goal
