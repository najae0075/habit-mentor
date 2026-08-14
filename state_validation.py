from __future__ import annotations

from typing import Any


TONE_VALUES = {"따뜻한 친구", "현실적인 코치", "짧고 단호한 트레이너", "유머 있는 동료"}
LIST_FIELDS = {"focus_habits", "checkin_dates", "completed"}
LIST_HISTORY_FIELDS = {"completion_history", "focus_history", "rest_history"}
DICT_HISTORY_FIELDS = {"checkin_history", "adjustment_history", "feedback_history", "reminder_history"}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _dict_history(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    return {
        day: entry
        for day, entry in value.items()
        if isinstance(day, str) and isinstance(entry, dict)
    }


def _list_history(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {
        day: _string_list(items)
        for day, items in value.items()
        if isinstance(day, str) and isinstance(items, list)
    }


def _custom_habits(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    valid = []
    required_strings = ("key", "icon", "category", "title")
    required_minutes = ("default_minutes", "reduced_minutes", "minimum_minutes")
    for item in value:
        if not isinstance(item, dict):
            continue
        if not all(isinstance(item.get(key), str) and item[key] for key in required_strings):
            continue
        if not all(isinstance(item.get(key), int) and item[key] >= 0 for key in required_minutes):
            continue
        valid.append({key: item[key] for key in (*required_strings, *required_minutes)})
    return valid


def _app_lock(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    salt = value.get("salt")
    digest = value.get("digest")
    try:
        if not isinstance(salt, str) or len(bytes.fromhex(salt)) != 16:
            return None
        if not isinstance(digest, str) or len(bytes.fromhex(digest)) != 32:
            return None
    except ValueError:
        return None
    return {"salt": salt, "digest": digest}


def normalize_saved_state(saved: Any) -> dict[str, Any]:
    if not isinstance(saved, dict):
        return {}
    result: dict[str, Any] = {}

    choices = {
        "condition": {"좋음", "보통", "나쁨"},
        "overtime": {"없어요", "있어요"},
        "motivation": {"낮음", "보통", "높음"},
        "tone": TONE_VALUES,
    }
    for key, allowed in choices.items():
        if saved.get(key) in allowed:
            result[key] = saved[key]

    for key in ("note", "active_date"):
        if isinstance(saved.get(key), str):
            result[key] = saved[key]
    if isinstance(saved.get("nickname"), str):
        result["nickname"] = saved["nickname"][:20]
    if isinstance(saved.get("available_minutes"), int) and 0 <= saved["available_minutes"] <= 1440:
        result["available_minutes"] = saved["available_minutes"]
    if isinstance(saved.get("sleep"), (int, float)) and 0 <= saved["sleep"] <= 24:
        result["sleep"] = float(saved["sleep"])
    if isinstance(saved.get("onboarding_complete"), bool):
        result["onboarding_complete"] = saved["onboarding_complete"]

    for key in LIST_FIELDS:
        if key in saved:
            result[key] = _string_list(saved[key])
    for key in LIST_HISTORY_FIELDS:
        if key in saved:
            result[key] = _list_history(saved[key])
    for key in DICT_HISTORY_FIELDS:
        if key in saved:
            result[key] = _dict_history(saved[key])

    for key in ("accepted",):
        if isinstance(saved.get(key), dict):
            result[key] = {
                habit: minutes
                for habit, minutes in saved[key].items()
                if isinstance(habit, str) and isinstance(minutes, int) and 0 <= minutes <= 1440
            }
    result["custom_habits"] = _custom_habits(saved.get("custom_habits", []))
    if "app_lock" in saved:
        result["app_lock"] = _app_lock(saved["app_lock"])

    reminder = saved.get("reminder_settings")
    if isinstance(reminder, dict):
        defaults = {"enabled": False, "moment": "아침", "morning_time": "08:00", "departure_time": "18:00", "habit_time": "20:00"}
        normalized = {**defaults}
        if isinstance(reminder.get("enabled"), bool):
            normalized["enabled"] = reminder["enabled"]
        if reminder.get("moment") in {"아침", "퇴근 전", "습관 시작 전"}:
            normalized["moment"] = reminder["moment"]
        for key in ("morning_time", "departure_time", "habit_time"):
            value = reminder.get(key)
            if isinstance(value, str) and len(value) == 5 and value[2] == ":":
                try:
                    hour, minute = map(int, value.split(":"))
                    if 0 <= hour < 24 and 0 <= minute < 60:
                        normalized[key] = value
                except ValueError:
                    pass
        result["reminder_settings"] = normalized

    return result
