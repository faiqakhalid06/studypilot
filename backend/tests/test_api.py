from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def body(**changes):
    data = {
        "hours_per_day": 2,
        "subjects": [{
            "name": "Machine Learning",
            "exam_date": (date.today() + timedelta(days=14)).isoformat(),
            "topics": [{"name": "Overfitting"}, {"name": "Decision Trees", "right": 1, "total": 4}],
        }],
    }
    data.update(changes)
    return data


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_plan_returns_seven_days_of_blocks():
    r = client.post("/api/plan", json=body())
    assert r.status_code == 200
    days = r.json()["days"]
    assert len(days) == 7
    assert sum(b["hours"] for b in days[0]["blocks"]) == 2


def test_plan_rejects_zero_hours():
    assert client.post("/api/plan", json=body(hours_per_day=0)).status_code == 422


def test_plan_rejects_subject_without_topics():
    bad = body()
    bad["subjects"][0]["topics"] = []
    assert client.post("/api/plan", json=bad).status_code == 422


def test_plan_rejects_right_more_than_total():
    bad = body()
    bad["subjects"][0]["topics"] = [{"name": "x", "right": 5, "total": 2}]
    assert client.post("/api/plan", json=bad).status_code == 422


NOTES = (
    "Overfitting happens when a model memorizes the training data instead of learning patterns. "
    "Regularization and more training data help reduce overfitting. "
    "Cross validation measures how well a model generalizes."
)


def subjects_body(**changes):
    data = {
        "subjects": [{
            "name": "Machine Learning",
            "exam_date": (date.today() + timedelta(days=14)).isoformat(),
            "topics": [
                {"name": "Overfitting", "notes": NOTES, "right": 1, "total": 4},
                {"name": "Trees", "notes": "Pruning removes branches to keep the tree simple."},
            ],
        }],
    }
    data.update(changes)
    return data


def test_quiz_endpoint_returns_questions():
    r = client.post("/api/quiz", json=subjects_body(count=3, seed=1))
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 3
    assert all("_____" in q["text"] and q["answer"] in q["options"] for q in qs)


def test_quiz_endpoint_rejects_zero_questions():
    assert client.post("/api/quiz", json=subjects_body(count=0)).status_code == 422


def test_weak_topics_endpoint():
    r = client.post("/api/weak-topics", json=subjects_body())
    assert r.status_code == 200
    rows = r.json()["topics"]
    assert [(x["topic"], x["status"]) for x in rows] == [("Overfitting", "weak"), ("Trees", "not tested")]