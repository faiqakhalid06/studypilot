import { useEffect, useState } from "react";
import "./App.css";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000") + "/api";

async function call(path, options) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let msg = "Request failed (" + res.status + ")";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
      else if (data.detail) msg = JSON.stringify(data.detail);
    } catch (e) {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

const emptyTopic = () => ({ name: "", notes: "" });

export default function App() {
  const [subjects, setSubjects] = useState([]);
  const [plan, setPlan] = useState(null);
  const [weak, setWeak] = useState([]);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [examDate, setExamDate] = useState("");
  const [topics, setTopics] = useState([emptyTopic()]);
  const [uploading, setUploading] = useState(false);

  const [quiz, setQuiz] = useState([]);
  const [picked, setPicked] = useState({});
  const [quizBusy, setQuizBusy] = useState(false);

  const [question, setQuestion] = useState("");
  const [tutor, setTutor] = useState(null);
  const [asking, setAsking] = useState(false);

  async function loadAll() {
    try {
      setError("");
      const [s, p, w] = await Promise.all([
        call("/subjects"),
        call("/plan"),
        call("/weak-topics"),
      ]);
      setSubjects(s);
      setPlan(p);
      setWeak(w.topics);
    } catch (e) {
      setError("Cannot reach the backend. Is the server running? " + e.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  function updateTopic(i, field, value) {
    setTopics(topics.map((t, idx) => (idx === i ? { ...t, [field]: value } : t)));
  }

  async function uploadFiles(files) {
    setUploading(true);
    const added = [];
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        setError("");
        const res = await fetch(API + "/extract-text", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed");
        const base = file.name.replace(/\.[^.]+$/, "");
        const size = 15000;
        const parts = Math.ceil(data.text.length / size);
        for (let p = 0; p < parts; p++) {
          added.push({
            name: parts > 1 ? base + " (part " + (p + 1) + ")" : base,
            notes: data.text.slice(p * size, (p + 1) * size),
          });
        }
      } catch (e) {
        setError(file.name + ": " + e.message);
      }
    }
    if (added.length) {
      setTopics((prev) => [...prev.filter((t) => t.name.trim() || t.notes.trim()), ...added]);
    }
    setUploading(false);
  }

  async function saveSubject(e) {
    e.preventDefault();
    try {
      setError("");
      const clean = topics.filter((t) => t.name.trim());
      await call("/subjects", {
        method: "POST",
        body: JSON.stringify({ name, exam_date: examDate, topics: clean }),
      });
      setName("");
      setExamDate("");
      setTopics([emptyTopic()]);
      loadAll();
    } catch (e) {
      setError(e.message);
    }
  }

  async function deleteSubject(id) {
    try {
      await call("/subjects/" + id, { method: "DELETE" });
      loadAll();
    } catch (e) {
      setError(e.message);
    }
  }

  async function loadQuiz(more) {
    setQuizBusy(true);
    try {
      setError("");
      const q = await call("/quiz/ai", {
        method: "POST",
        body: JSON.stringify({ count: 5, asked: more ? quiz.map((x) => x.text) : [] }),
      });
      const offset = more ? quiz.length : 0;
      const fresh = q.questions.map((x, i) => ({ ...x, id: offset + i + 1 }));
      setQuiz(more ? [...quiz, ...fresh] : fresh);
      if (!more) setPicked({});
    } catch (e) {
      setError(e.message);
    }
    setQuizBusy(false);
  }

  function findTopicId(q) {
    const s = subjects.find((s) => s.name === q.subject);
    const t = s && s.topics.find((t) => t.name === q.topic);
    return t ? t.id : null;
  }

  async function answer(q, option) {
    if (picked[q.id]) return;
    setPicked({ ...picked, [q.id]: option });
    const id = findTopicId(q);
    if (id === null) return;
    try {
      await call("/topics/" + id + "/answers", {
        method: "POST",
        body: JSON.stringify({ correct: option === q.answer }),
      });
      loadAll();
    } catch (e) {
      setError(e.message);
    }
  }

  async function askTutor() {
    if (question.trim().length < 3) return;
    setAsking(true);
    setTutor(null);
    try {
      setError("");
      setTutor(await call("/tutor/ask", { method: "POST", body: JSON.stringify({ question }) }));
    } catch (e) {
      setError(e.message);
    }
    setAsking(false);
  }

  const badge = (s) =>
    s === "weak" ? "badge weak-b" : s === "ok" ? "badge ok-b" : "badge nt-b";

  return (
    <div className="wrap">
      <h1>StudyPilot</h1>
      <div className="sub">Your study plan, quiz and AI tutor in one place.</div>
      {error && <div className="err">{error}</div>}

      <div className="grid">
        <div className="card">
          <h2>1. Add a subject</h2>
          <form onSubmit={saveSubject}>
            <input placeholder="Subject name (e.g. Machine Learning)" value={name}
              onChange={(e) => setName(e.target.value)} required />
            <input type="date" value={examDate}
              onChange={(e) => setExamDate(e.target.value)} required />

            <div style={{ marginBottom: 8 }}>
              <b>Upload files</b> (PDF, Word, PowerPoint, TXT)
              <input type="file" multiple
                onChange={(e) => { uploadFiles([...e.target.files]); e.target.value = ""; }} />
              {uploading && <div style={{ color: "#6b7280", fontSize: 13 }}>Reading files...</div>}
            </div>

            {topics.map((t, i) => (
              <div className="topicbox" key={i}>
                <input placeholder="Topic name" value={t.name}
                  onChange={(e) => updateTopic(i, "name", e.target.value)} />
                <textarea rows={3} placeholder="Notes for this topic" value={t.notes}
                  onChange={(e) => updateTopic(i, "notes", e.target.value)} />
              </div>
            ))}
            <button type="button" className="light"
              onClick={() => setTopics([...topics, emptyTopic()])}>+ Topic</button>
            <button type="submit" disabled={uploading}>Save subject</button>
          </form>
        </div>

        <div className="card">
          <h2>Your subjects</h2>
          {subjects.length === 0 && <div>No subjects yet.</div>}
          {subjects.map((s) => (
            <div className="row" key={s.id}>
              <div>
                <b>{s.name}</b>
                <div style={{ fontSize: 13, color: "#6b7280" }}>
                  Exam: {s.exam_date} · {s.topics.length} topics
                </div>
              </div>
              <button className="red" onClick={() => deleteSubject(s.id)}>Delete</button>
            </div>
          ))}
        </div>

        <div className="card">
          <h2>2. Weekly plan</h2>
          {plan && plan.days.length === 0 && <div>Add a subject to get a plan.</div>}
          {plan && plan.days.map((d) => (
            <div className="day" key={d.date}>
              <b>{d.date}</b>
              {d.blocks.map((b, i) => (
                <div className={b.reason.includes("weak") ? "block weak" : "block"} key={i}>
                  <span>{b.subject} · {b.topic}</span>
                  <span>{b.hours}h · {b.reason}</span>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="card">
          <h2>3. Weak topics</h2>
          {weak.length === 0 && <div>Nothing yet.</div>}
          {weak.map((t, i) => (
            <div className="row" key={i}>
              <span>{t.subject} · {t.topic}</span>
              <span className={badge(t.status)}>
                {t.status}{t.score_percent !== null ? " (" + t.score_percent + "%)" : ""}
              </span>
            </div>
          ))}
        </div>

        <div className="card full">
          <h2>4. Quiz</h2>
          <button onClick={() => loadQuiz(false)} disabled={quizBusy}>
            {quizBusy ? "Making questions..." : "Start a 5-question quiz"}
          </button>
          {quiz.length > 0 && (
            <button className="light" onClick={() => loadQuiz(true)} disabled={quizBusy}>
              + 5 more questions
            </button>
          )}
          {quiz.map((q) => (
            <div key={q.id} style={{ marginTop: 14 }}>
              <div><b>{q.id}.</b> {q.text} <i style={{ color: "#6b7280" }}>({q.topic})</i></div>
              {q.options.map((o) => {
                const chosen = picked[q.id];
                let cls = "opt";
                if (chosen && o === q.answer) cls += " good";
                else if (chosen === o) cls += " bad";
                return (
                  <button key={o} className={cls} onClick={() => answer(q, o)}>{o}</button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="card full">
          <h2>5. Ask the AI tutor</h2>
          <input placeholder="Ask about your notes, e.g. How can I reduce overfitting?"
            value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askTutor()} />
          <button onClick={askTutor} disabled={asking}>{asking ? "Thinking..." : "Ask"}</button>
          {tutor && (
            <div style={{ marginTop: 12 }}>
              <div>{tutor.answer}</div>
              {tutor.sources.map((s, i) => (
                <div className="src" key={i}>
                  <b>[{i + 1}] {s.subject_name} / {s.topic_name}:</b> {s.text}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}