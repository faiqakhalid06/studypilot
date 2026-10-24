import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (makes sure the tables are known)
from app.database import Base, engine
from app.planner import make_plan
from app.progress import find_topics
from app.quiz import make_quiz
from app.routes import router
from app.schemas import (
    PlanRequest, PlanResponse, QuizRequest, QuizResponse, TopicsRequest, TopicsResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)       # create the tables if they do not exist yet
    yield


app = FastAPI(title="StudyPilot API", lifespan=lifespan)
from fastapi.middleware.cors import CORSMiddleware

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL").rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/plan", response_model=PlanResponse)
def create_plan(request: PlanRequest):
    """Make a plan from data sent in the request (nothing is saved)."""
    return make_plan(request)


@app.post("/api/quiz", response_model=QuizResponse)
def create_quiz(request: QuizRequest):
    """Make a quiz from data sent in the request (nothing is saved)."""
    return make_quiz(request)


@app.post("/api/weak-topics", response_model=TopicsResponse)
def weak_topics(request: TopicsRequest):
    """List topics as weak, ok or not tested from data sent in the request."""
    return find_topics(request.subjects)