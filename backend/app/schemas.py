from datetime import date

from pydantic import BaseModel, Field, model_validator


class TopicIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=20000)
    right: int = Field(default=0, ge=0)    # quiz answers the student got right
    total: int = Field(default=0, ge=0)    # quiz answers the student gave in total

    @model_validator(mode="after")
    def right_cannot_be_more_than_total(self):
        if self.right > self.total:
            raise ValueError("right cannot be more than total")
        return self


class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    exam_date: date
    topics: list[TopicIn] = Field(min_length=1, max_length=50)


class PlanRequest(BaseModel):
    subjects: list[SubjectIn] = Field(max_length=20)
    hours_per_day: float = Field(default=2, ge=0.5, le=12)
    start_date: date | None = None         # default: today
    days: int = Field(default=7, ge=1, le=14)


class PlanBlock(BaseModel):
    subject: str
    topic: str
    hours: float
    reason: str


class PlanDay(BaseModel):
    date: date
    blocks: list[PlanBlock]


class PlanResponse(BaseModel):
    hours_per_day: float
    days: list[PlanDay]


# ---------- Milestone 2: quiz and weak topics ----------
class QuizRequest(BaseModel):
    subjects: list[SubjectIn] = Field(max_length=20)
    count: int = Field(default=5, ge=1, le=20)
    seed: int | None = None                # same seed -> same quiz (useful for tests)


class QuizQuestion(BaseModel):
    id: int
    subject: str
    topic: str
    text: str                              # the sentence with a blank: _____
    options: list[str]
    answer: str                            # for now the server sends it; later it stays on the server


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]


class TopicsRequest(BaseModel):
    subjects: list[SubjectIn] = Field(max_length=20)


class TopicStatus(BaseModel):
    subject: str
    topic: str
    score_percent: int | None              # None = not tested yet
    status: str                            # "weak", "ok" or "not tested"


class TopicsResponse(BaseModel):
    topics: list[TopicStatus]


# ---------- Milestone 3: saved data ----------
class AnswerIn(BaseModel):
    correct: bool


class TopicOut(BaseModel):
    id: int
    name: str
    notes: str
    right: int
    total: int


class SubjectOut(BaseModel):
    id: int
    name: str
    exam_date: date
    topics: list[TopicOut]