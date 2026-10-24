import json
import random
from datetime import date

from pydantic import BaseModel, Field

from app.llm import generate
from app.planner import weakness
from app.quiz import make_quiz
from app.schemas import QuizQuestion, QuizRequest, QuizResponse


class AiQuizRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=10)
    asked: list[str] = Field(default_factory=list, max_length=200)  # questions already shown


def pick_window(notes: str, size: int = 3000) -> str:
    """A random piece of a long file, so each round covers a different part."""
    if len(notes) <= size:
        return notes
    start = random.randint(0, len(notes) - size)
    return notes[start : start + size]


def fallback(request: QuizRequest, asked: list[str]) -> QuizResponse:
    old = make_quiz(request).questions
    fresh = [q for q in old if q.text not in asked]
    for i, q in enumerate(fresh, 1):
        q.id = i
    return QuizResponse(questions=fresh)


def make_ai_quiz(request: QuizRequest, asked: list[str]) -> QuizResponse:
    today = date.today()
    entries = [
        (s.name, t)
        for s in request.subjects
        if s.exam_date >= today
        for t in s.topics
        if t.notes.strip()
    ]
    if not entries:
        return fallback(request, asked)

    entries.sort(key=lambda e: -weakness(e[1]))  # weakest topics first
    chosen = entries[:3]

    material = "\n\n".join(
        f"Material {i} ({subject} / {topic.name}):\n{pick_window(topic.notes)}"
        for i, (subject, topic) in enumerate(chosen, 1)
    )
    avoid = "\n".join("- " + q for q in asked[-40:]) or "(none)"
    prompt = (
        f"You are a teacher. Write {request.count} multiple-choice questions using ONLY the study material below.\n"
        "Rules:\n"
        "- Each question has exactly 4 options and exactly one correct answer.\n"
        "- The answer must be written exactly the same as one of the options.\n"
        "- Spread the questions across the materials.\n"
        "- Do not repeat any of these earlier questions:\n" + avoid + "\n\n"
        "Reply with ONLY a JSON array and nothing else. Each item looks like:\n"
        '{"material": 1, "question": "...", "options": ["a", "b", "c", "d"], "answer": "a"}\n\n'
        + material
    )

    try:
        raw = generate(prompt)
        data = json.loads(raw[raw.find("[") : raw.rfind("]") + 1])
    except Exception as exc:
        print("[ai_quiz] falling back:", str(exc)[:120])
        return fallback(request, asked)

    questions: list[QuizQuestion] = []
    for item in data:
        try:
            subject, topic = chosen[int(item["material"]) - 1]
            options = [str(o).strip() for o in item["options"]]
            answer = str(item["answer"]).strip()
            text = str(item["question"]).strip()
            if len(options) != 4 or len(set(options)) != 4 or answer not in options:
                continue
            if not text or text in asked:
                continue
            random.shuffle(options)
            questions.append(QuizQuestion(
                id=len(questions) + 1, subject=subject, topic=topic.name,
                text=text, options=options, answer=answer,
            ))
        except Exception:
            continue

    return QuizResponse(questions=questions[: request.count]) if questions else fallback(request, asked)