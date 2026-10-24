from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.planner import make_plan, reason, weakness
from app.schemas import PlanRequest, SubjectIn, TopicIn

TODAY = date(2026, 10, 23)


def topic(name, right=0, total=0):
    return TopicIn(name=name, right=right, total=total)


def subject(name, days_to_exam, topics):
    return SubjectIn(name=name, exam_date=TODAY + timedelta(days=days_to_exam), topics=topics)


def plan(subjects, hours=2, days=7):
    return make_plan(PlanRequest(subjects=subjects, hours_per_day=hours, days=days, start_date=TODAY))


def hours_by_topic(p):
    totals = {}
    for day in p.days:
        for b in day.blocks:
            totals[b.topic] = totals.get(b.topic, 0) + b.hours
    return totals


def test_weakness_values():
    assert weakness(topic("a")) == 0.6
    assert weakness(topic("a", right=5, total=5)) == 0
    assert weakness(topic("a", right=0, total=5)) == 1


def test_right_cannot_be_more_than_total():
    with pytest.raises(ValidationError):
        TopicIn(name="a", right=6, total=5)


def test_plan_has_the_asked_number_of_days():
    assert len(plan([subject("ML", 20, [topic("a")])]).days) == 7
    assert len(plan([subject("ML", 20, [topic("a")])], days=3).days) == 3


def test_every_day_uses_all_the_hours():
    p = plan([subject("ML", 20, [topic("a"), topic("b"), topic("c")])], hours=2.5)
    for day in p.days:
        assert sum(b.hours for b in day.blocks) == 2.5


def test_weak_topic_gets_more_time_than_strong_topic():
    p = plan([subject("ML", 20, [topic("weak", 1, 5), topic("strong", 4, 5)])])
    h = hours_by_topic(p)
    assert h["weak"] > h["strong"]


def test_every_topic_still_gets_some_time():
    p = plan([subject("ML", 20, [topic("weak", 0, 5), topic("strong", 5, 5)])])
    assert hours_by_topic(p)["strong"] > 0


def test_closer_exam_gets_more_time():
    p = plan([
        subject("Soon", 4, [topic("soon-topic")]),
        subject("Later", 25, [topic("later-topic")]),
    ])
    h = hours_by_topic(p)
    assert h["soon-topic"] > h["later-topic"]


def test_nothing_is_planned_after_the_exam_day():
    p = plan([subject("ML", 2, [topic("a")])])
    assert [len(d.blocks) > 0 for d in p.days] == [True, True, True, False, False, False, False]


def test_past_exam_gets_no_time():
    p = plan([subject("Old", -3, [topic("a")]), subject("New", 10, [topic("b")])])
    assert "a" not in hours_by_topic(p)
    assert hours_by_topic(p)["b"] > 0


def test_no_subjects_gives_empty_days():
    p = plan([])
    assert len(p.days) == 7
    assert all(d.blocks == [] for d in p.days)


def test_same_input_same_plan():
    subjects = [subject("ML", 20, [topic("a", 1, 3), topic("b"), topic("c", 3, 3)])]
    assert plan(subjects) == plan(subjects)


def test_reason_labels():
    far = TODAY + timedelta(days=30)
    near = TODAY + timedelta(days=2)
    assert reason(topic("a", 0, 4), far, TODAY) == "weak topic"
    assert reason(topic("a"), far, TODAY) == "not tested yet"
    assert reason(topic("a", 4, 4), far, TODAY) == "steady review"
    assert reason(topic("a"), near, TODAY) == "exam soon"


def test_plan_blocks_carry_the_reason():
    p = plan([subject("ML", 30, [topic("weak", 0, 4)])], days=1)
    assert p.days[0].blocks[0].reason == "weak topic"