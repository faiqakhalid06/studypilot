from datetime import date, timedelta

from app.progress import find_topics, topic_status
from app.schemas import SubjectIn, TopicIn

TODAY = date(2026, 10, 23)


def subject(name, days, topics):
    return SubjectIn(name=name, exam_date=TODAY + timedelta(days=days), topics=topics)


def test_status_values():
    assert topic_status(0, 0) == (None, "not tested")
    assert topic_status(2, 5) == (40, "weak")
    assert topic_status(3, 5) == (60, "ok")
    assert topic_status(5, 5) == (100, "ok")


def test_order_is_weak_then_not_tested_then_ok():
    s = subject("ML", 10, [
        TopicIn(name="good", right=5, total=5),
        TopicIn(name="new"),
        TopicIn(name="bad", right=1, total=5),
        TopicIn(name="worse", right=0, total=5),
    ])
    names = [t.topic for t in find_topics([s], today=TODAY).topics]
    assert names == ["worse", "bad", "new", "good"]


def test_past_exam_subjects_are_not_listed():
    s = subject("Old", -2, [TopicIn(name="a")])
    assert find_topics([s], today=TODAY).topics == []


def test_topics_from_several_subjects_are_listed():
    a = subject("ML", 10, [TopicIn(name="a", right=1, total=4)])
    b = subject("DS", 10, [TopicIn(name="b", right=4, total=4)])
    rows = find_topics([a, b], today=TODAY).topics
    assert [(r.subject, r.status) for r in rows] == [("ML", "weak"), ("DS", "ok")]