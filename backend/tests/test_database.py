from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

NOTES = (
    "Overfitting happens when a model memorizes the training data instead of learning patterns. "
    "Regularization and more training data help reduce overfitting. "
    "Cross validation measures how well a model generalizes."
)


@pytest.fixture
def client():
    """A fresh empty database in memory for every test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def subject_body(name="Machine Learning", days=14):
    return {
        "name": name,
        "exam_date": (date.today() + timedelta(days=days)).isoformat(),
        "topics": [
            {"name": "Overfitting", "notes": NOTES},
            {"name": "Trees", "notes": "Pruning removes branches to keep the tree simple."},
        ],
    }


def add(client, **kw):
    r = client.post("/api/subjects", json=subject_body(**kw))
    assert r.status_code == 201
    return r.json()


def test_list_is_empty_at_the_start(client):
    assert client.get("/api/subjects").json() == []


def test_saved_subject_gets_ids_and_can_be_listed(client):
    saved = add(client)
    assert saved["id"] >= 1
    assert [t["name"] for t in saved["topics"]] == ["Overfitting", "Trees"]
    assert all(t["id"] >= 1 and t["right"] == 0 and t["total"] == 0 for t in saved["topics"])
    assert client.get("/api/subjects").json() == [saved]


def test_bad_subject_is_rejected(client):
    bad = subject_body()
    bad["topics"] = []
    assert client.post("/api/subjects", json=bad).status_code == 422


def test_delete_removes_subject_and_its_topics(client):
    saved = add(client)
    assert client.delete(f"/api/subjects/{saved['id']}").status_code == 204
    assert client.get("/api/subjects").json() == []
    topic_id = saved["topics"][0]["id"]
    assert client.post(f"/api/topics/{topic_id}/answers", json={"correct": True}).status_code == 404


def test_delete_unknown_subject_is_404(client):
    assert client.delete("/api/subjects/999").status_code == 404


def test_answers_update_right_and_total(client):
    topic_id = add(client)["topics"][0]["id"]
    client.post(f"/api/topics/{topic_id}/answers", json={"correct": True})
    r = client.post(f"/api/topics/{topic_id}/answers", json={"correct": False})
    assert (r.json()["right"], r.json()["total"]) == (1, 2)


def test_answer_for_unknown_topic_is_404(client):
    assert client.post("/api/topics/999/answers", json={"correct": True}).status_code == 404


def test_answers_are_kept_between_requests(client):
    saved = add(client)
    topic_id = saved["topics"][0]["id"]
    client.post(f"/api/topics/{topic_id}/answers", json={"correct": True})
    listed = client.get("/api/subjects").json()[0]["topics"][0]
    assert (listed["right"], listed["total"]) == (1, 1)


def test_saved_plan_has_seven_days_and_uses_saved_subjects(client):
    add(client)
    days = client.get("/api/plan").json()["days"]
    assert len(days) == 7
    assert days[0]["blocks"]


def test_saved_plan_with_nothing_saved_is_empty(client):
    days = client.get("/api/plan").json()["days"]
    assert len(days) == 7 and all(d["blocks"] == [] for d in days)


def test_wrong_answers_give_that_topic_more_study_time(client):
    saved = add(client)
    weak_id = saved["topics"][1]["id"]            # "Trees"

    def tree_hours():
        days = client.get("/api/plan").json()["days"]
        return sum(b["hours"] for d in days for b in d["blocks"] if b["topic"] == "Trees")

    before = tree_hours()
    for _ in range(5):
        client.post(f"/api/topics/{weak_id}/answers", json={"correct": False})
    assert tree_hours() > before


def test_weak_topics_follow_the_saved_answers(client):
    saved = add(client)
    topic_id = saved["topics"][0]["id"]
    client.post(f"/api/topics/{topic_id}/answers", json={"correct": True})
    for _ in range(3):
        client.post(f"/api/topics/{topic_id}/answers", json={"correct": False})
    rows = client.get("/api/weak-topics").json()["topics"]
    assert (rows[0]["topic"], rows[0]["status"], rows[0]["score_percent"]) == ("Overfitting", "weak", 25)


def test_saved_quiz_uses_saved_notes(client):
    add(client)
    r = client.get("/api/quiz?count=3&seed=1")
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 3 and all("_____" in q["text"] for q in qs)


def test_bad_query_values_are_rejected(client):
    assert client.get("/api/plan?hours_per_day=0").status_code == 422
    assert client.get("/api/quiz?count=0").status_code == 422