from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Habit:
    key: str
    icon: str
    category: str
    title: str
    default_minutes: int
    reduced_minutes: int
    minimum_minutes: int


DEFAULT_HABITS = [
    Habit("side_project", "✦", "성장", "사이드 프로젝트", 40, 20, 5),
    Habit("stretch", "◒", "건강", "저녁 스트레칭", 20, 10, 2),
    Habit("reading", "▤", "마음", "잠들기 전 독서", 20, 10, 5),
]


def habit_to_dict(habit: Habit) -> dict[str, Any]:
    return asdict(habit)


def build_habits(custom_habits: list[dict[str, Any]]) -> list[Habit]:
    return [*DEFAULT_HABITS, *(Habit(**item) for item in custom_habits)]


def select_focused(habits: list[Habit], selected_keys: list[str], limit: int = 3) -> list[Habit]:
    selected = set(selected_keys)
    return [habit for habit in habits if habit.key in selected][:limit]
