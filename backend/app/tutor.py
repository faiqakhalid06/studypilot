import re

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm import generate
from app.models import Topic

STOP_WORDS = {
    "the", "and", "for", "are", "what", "how", "why", "when", "which", "who",
    "does", "did", "can", "this", "that", "with", "from", "about", "into",
    "your", "you", "was", "were", "has", "have", "had", "its", "than", "then",
    "explain", "tell", "give", "mean", "means",
}


class TutorQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    subject_id: int | None = None


class TutorSource(BaseModel):
    topic_id: int
    topic_name: str
    subject_name: str
    text: str


class TutorAnswer(BaseModel):
    answer: str
    sources: list[TutorSource]


def words(text: str) -> set[str]:
    """Lowercase keywords, with a simple plural fix so 'trees' matches 'tree'."""
    result = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        if len(w) > 2 and w not in STOP_WORDS:
            result.add(w)
    return result


def chunk_notes(notes: str, sentences_per_chunk: int = 2) -> list[str]:
    """Split notes into small pieces of a few sentences each."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", notes.strip()) if s.strip()]
    return [
        " ".join(sentences[i : i + sentences_per_chunk])
        for i in range(0, len(sentences), sentences_per_chunk)
    ]


def retrieve(db: Session, question: str, subject_id: int | None, top_k: int = 5) -> list[TutorSource]:
    """Return the note pieces that best match the question."""
    query = words(question)
    stmt = select(Topic).order_by(Topic.id)
    if subject_id is not None:
        stmt = stmt.where(Topic.subject_id == subject_id)

    scored = []
    for topic in db.scalars(stmt).all():
        name_bonus = 0.5 * len(query & words(topic.name))
        for chunk in chunk_notes(topic.notes):
            overlap = len(query & words(chunk))
            if overlap > 0:
                source = TutorSource(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    subject_name=topic.subject.name,
                    text=chunk,
                )
                scored.append((overlap + name_bonus, source))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [source for _, source in scored[:top_k]]


def build_prompt(question: str, sources: list[TutorSource]) -> str:
    notes = "\n".join(
        f"[{i}] ({s.subject_name} / {s.topic_name}) {s.text}" for i, s in enumerate(sources, 1)
    )
    return (
        "You are a friendly study tutor. Answer the student's question using ONLY the notes below.\n"
        "If the notes do not contain the answer, say you could not find it in the notes.\n"
        "Keep the answer short and simple, and mention the note numbers you used, like [1].\n\n"
        f"Notes:\n{notes}\n\n"
        f"Question: {question}"
    )


def ask_tutor(db: Session, body: TutorQuestion) -> TutorAnswer:
    sources = retrieve(db, body.question, body.subject_id)
    if not sources:
        # Nothing matched, so we skip Gemini. This avoids made-up answers and saves free quota.
        return TutorAnswer(
            answer="I could not find this in your notes. Try adding notes for this topic first.",
            sources=[],
        )
    try:
        answer = generate(build_prompt(body.question, sources))
    except Exception:
        # AI is busy: still help the student by showing the matching notes.
        answer = "The AI is busy right now. Here is what your notes say:\n\n" + "\n\n".join(
            s.text for s in sources
        )
    return TutorAnswer(answer=answer, sources=sources)