from __future__ import annotations

from domain.habits import Habit


def recommend_habit(
    habit: Habit,
    *,
    condition: str,
    has_overtime: bool,
    motivation: str,
    sleep_hours: float,
    available_minutes: int,
    recent_feedback: str | None = None,
) -> dict[str, object]:
    if sleep_hours < 5 and condition == "나쁨":
        return {
            "level": "회복",
            "minutes": 0,
            "title": "오늘은 편안히 쉬기",
            "reason": "수면과 컨디션을 고려해 오늘은 회복을 우선해요.",
        }

    constraints = sum((condition == "나쁨", has_overtime, motivation == "낮음"))
    if recent_feedback == "버거웠어요":
        constraints += 1
    if constraints >= 2:
        amount = min(habit.minimum_minutes, available_minutes)
        return {
            "level": "최소",
            "minutes": amount,
            "title": f"{amount}분만 가볍게 시작하기",
            "reason": "야근과 현재 에너지를 고려해 연결만 이어갈 만큼 줄였어요.",
        }
    if constraints == 1 or available_minutes < habit.default_minutes:
        amount = max(habit.minimum_minutes, min(habit.reduced_minutes, available_minutes))
        return {
            "level": "축소",
            "minutes": amount,
            "title": f"{amount}분만 집중하기",
            "reason": (
                "최근 난이도 피드백과 오늘 쓸 수 있는 시간을 반영해 무리 없도록 조정했어요."
                if recent_feedback
                else "오늘 쓸 수 있는 시간 안에서 무리 없도록 조정했어요."
            ),
        }
    return {
        "level": "기본",
        "minutes": habit.default_minutes,
        "title": f"{habit.default_minutes}분 집중하기",
        "reason": "오늘은 기본 목표를 충분히 해낼 수 있는 상태예요.",
    }
