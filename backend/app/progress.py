from datetime import date

from app.schemas import SubjectIn, TopicStatus, TopicsResponse

WEAK_BELOW = 0.6


def topic_status(right: int, total: int) -> tuple[int | None, str]:
    if total == 0:
        return None, "not tested"
    score = right / total
    return round(score * 100), "weak" if score < WEAK_BELOW else "ok"


def find_topics(subjects: list[SubjectIn], today: date | None = None) -> TopicsResponse:
    today = today or date.today()
    rows: list[TopicStatus] = []
    for s in subjects:
        if s.exam_date < today:
            continue
        for t in s.topics:
            percent, status = topic_status(t.right, t.total)
            rows.append(TopicStatus(subject=s.name, topic=t.name, score_percent=percent, status=status))

    order = {"weak": 0, "not tested": 1, "ok": 2}
    rows.sort(key=lambda r: (order[r.status], r.score_percent if r.score_percent is not None else 0))
    return TopicsResponse(topics=rows)