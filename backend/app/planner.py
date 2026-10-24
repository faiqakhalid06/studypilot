from datetime import date, timedelta
from math import sqrt

from app.schemas import (
    PlanBlock, PlanDay, PlanRequest, PlanResponse, SubjectIn, TopicIn,
)

UNTESTED_WEAKNESS = 0.6


def weakness(topic: TopicIn) -> float:
    """0 = all quiz answers right, 1 = all wrong, 0.6 = not tested yet."""
    if topic.total == 0:
        return UNTESTED_WEAKNESS
    return 1 - topic.right / topic.total


def weight(topic: TopicIn, exam_date: date, day: date) -> float:
    days_left = max(1, (exam_date - day).days)
    return (0.2 + weakness(topic)) / sqrt(days_left)


def reason(topic: TopicIn, exam_date: date, day: date) -> str:
    if topic.total and weakness(topic) > 0.5:
        return "weak topic"
    if (exam_date - day).days <= 3:
        return "exam soon"
    if topic.total == 0:
        return "not tested yet"
    return "steady review"


def make_plan(request: PlanRequest, today: date | None = None) -> PlanResponse:
    start = request.start_date or today or date.today()
    entries: list[tuple[SubjectIn, TopicIn]] = [
        (s, t) for s in request.subjects for t in s.topics
    ]
    used = [0] * len(entries)                       # blocks given so far, per topic
    blocks_per_day = round(request.hours_per_day * 2)
    days: list[PlanDay] = []

    for offset in range(request.days):
        day = start + timedelta(days=offset)
        open_topics = [i for i, (s, _) in enumerate(entries) if s.exam_date >= day]
        counts: dict[int, int] = {}

        if open_topics:
            w = {i: weight(entries[i][1], entries[i][0].exam_date, day) for i in open_topics}
            for _ in range(blocks_per_day):
                best = open_topics[0]
                for i in open_topics[1:]:
                    if w[i] / (used[i] + 1) > w[best] / (used[best] + 1):
                        best = i
                used[best] += 1
                counts[best] = counts.get(best, 0) + 1

        blocks = [
            PlanBlock(
                subject=entries[i][0].name,
                topic=entries[i][1].name,
                hours=c / 2,
                reason=reason(entries[i][1], entries[i][0].exam_date, day),
            )
            for i, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        days.append(PlanDay(date=day, blocks=blocks))

    return PlanResponse(hours_per_day=request.hours_per_day, days=days)