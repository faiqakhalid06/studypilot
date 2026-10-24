# StudyPilot

Smart study planner and AI tutor. Students upload PDF, Word or PowerPoint notes. The app:
- makes a weekly study plan from the subject and exam date
- writes quiz questions from the files (5 at a time, with more on request)
- finds weak topics from quiz results and gives them more study time
- answers questions from the notes and shows the source (Gemini + RAG)

Tech: FastAPI, SQLAlchemy (SQLite), Gemini API, React (Vite).

## Run it

You need Python 3.11+, Node.js (LTS) and a free Gemini API key from Google AI Studio.

### Backend
```
python -m venv .venv
.venv\Scripts\activate
cd backend
pip install -r requirements.txt
```
Create `backend/.env` with:
```
GEMINI_API_KEY=your_key_here
```
Then start it:
```
python -m uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### Frontend
In a second terminal:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Limits
- Scanned PDFs (images) and old .doc/.ppt files are not supported yet.
- Tutor search is keyword-based. Embeddings are the next upgrade.
- If Gemini is busy, the quiz falls back to a simple rule-based quiz.