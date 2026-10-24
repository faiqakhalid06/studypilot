import random
import re
from datetime import date

from app.planner import weakness
from app.schemas import QuizQuestion, QuizRequest, QuizResponse, TopicIn

STOP_WORDS = set(
    "about which their there these those where because between while using should would "
    "could other often every after before under over each from with that this have been "
    "when what does into than then them they your".split()
)
BLANK = "_____"


def words(text: str) -> list[str]:
    """Important words: letters only, at least 5 letters, not a common word."""
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 5 and w not in STOP_WORDS]


def sentences(notes: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n", notes)
    return [p.strip() for p in parts if len(p.split()) >= 5]


def make_quiz(request: QuizRequest, today: date | None = None) -> QuizResponse:
    today = today or date.today()
    rng = random.Random(request.seed)

    entries: list[tuple[str, TopicIn]] = [
        (s.name, t) for s in request.subjects if s.exam_date >= today for t in s.topics
    ]
    entries.sort(key=lambda e: -weakness(e[1]))        # weakest first (stable)
    pool = sorted({w for _, t in entries for w in words(t.notes)})

    questions: list[QuizQuestion] = []
    used: set[str] = set()
    cursor = [0] * len(entries)                        # which sentence each topic is on
    sent_lists = [sentences(t.notes) for _, t in entries]
    for lst in sent_lists:
        rng.shuffle(lst)

    progress = True
    while len(questions) < request.count and progress:
        progress = False
        for i, (subject, topic) in enumerate(entries):
            if len(questions) >= request.count:
                break
            while cursor[i] < len(sent_lists[i]):
                sentence = sent_lists[i][cursor[i]]
                cursor[i] += 1
                if sentence in used:
                    continue
                candidates = words(sentence)
                if not candidates:
                    continue
                answer = max(candidates, key=len)       # first of the longest
                wrong = [w for w in pool if w != answer]
                if len(wrong) < 1:
                    continue
                options = rng.sample(wrong, min(3, len(wrong))) + [answer]
                rng.shuffle(options)
                text = re.sub(rf"\b{re.escape(answer)}\b", BLANK, sentence, count=1, flags=re.I)
                used.add(sentence)
                questions.append(QuizQuestion(
                    id=len(questions) + 1, subject=subject, topic=topic.name,
                    text=text, options=options, answer=answer,
                ))
                progress = True
                break

    return QuizResponse(questions=questions)