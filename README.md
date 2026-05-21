# ⚡ AI Dev Manager

A **local-first AI engineering assistant** for developers and small teams. Scan repositories, chat with your codebase, generate tasks, debug errors, and manage projects — all stored securely on your machine.

```
AI Dev Manager = AI Chat + Repo RAG + Task Planner + Debugger + Local Memory
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **Repository Scanner** | Scans folders, detects tech stack, maps file structure |
| 💬 **AI Chat** | Context-aware chat using your codebase as RAG context |
| 🤖 **Multi-Agent System** | Planning, Coding, Debugging, Documentation agents |
| ✅ **Task Planner** | AI generates sprint tasks from feature descriptions |
| 🐛 **Debugger** | Paste stack traces → get root cause + fix |
| 🧠 **Persistent Memory** | ChromaDB vector store + SQLite, everything local |
| 📝 **Documentation** | Auto-generate README and architecture summaries |
| 🔒 **Local-First** | Zero cloud databases, all data stays on your machine |

---

## 🗂 Project Structure

```
ai-dev-manager/
├── app/
│   ├── agents/
│   │   └── agents.py          # AI agents (Planning, Coding, Debug, Docs)
│   ├── database/
│   │   ├── sqlite_manager.py  # All SQLite DB operations
│   │   └── app.db             # Auto-created SQLite database
│   ├── memory/
│   │   ├── vector_store.py    # ChromaDB vector memory manager
│   │   └── chroma_db/         # Auto-created vector store
│   ├── repository/
│   │   └── scanner.py         # Local repo scanner
│   ├── orchestration/         # Agent orchestration utilities
│   ├── ui/
│   │   └── streamlit_app.py   # Full Streamlit frontend
│   └── main.py                # FastAPI backend
├── uploads/                   # File uploads
├── logs/                      # Application logs
├── run.py                     # Unified launcher
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd ai-dev-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Get your API key at: https://console.anthropic.com

### 3. Run

```bash
python run.py
```

- **UI**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🛠 Tech Stack

### Backend
- **FastAPI** — REST API backend
- **SQLite + SQLAlchemy** — Local persistent database
- **ChromaDB** — Local vector embeddings (no cloud)

### Frontend
- **Streamlit** — Developer dashboard UI

### AI
- **Anthropic Claude** (claude-sonnet-4) — All AI operations
- **RAG** — Repository-aware chat using local vector search

---

## 📋 SQLite Tables

| Table | Purpose |
|---|---|
| `users` | User accounts (hashed passwords) |
| `projects` | Project metadata and tech stack |
| `conversations` | Full chat history per project |
| `tasks` | Task tracker with status/priority |
| `bug_reports` | Debug history and AI analysis |
| `memory_logs` | Architecture summaries and insights |
| `activity_logs` | Audit trail of all actions |

---

## 🤖 AI Agents

| Agent | Role |
|---|---|
| **General** | Open-ended dev questions |
| **Planning** | Feature → task breakdown |
| **Coding** | Code review & implementation |
| **Repo Chat** | Codebase Q&A with RAG |
| **Debugging** | Error analysis & fixes |
| **Documentation** | README & architecture docs |

---

## 🔒 Security

- Passwords hashed with SHA-256
- API keys in environment variables only
- Path traversal protection on all file operations
- Input sanitization against prompt injection
- Rate limiting (30 req/min by default)
- File size limits on uploads

---

## ⚙️ Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...       # Required
SECRET_KEY=random-secret            # JWT secret
DATABASE_URL=sqlite:///./app/database/app.db
CHROMA_PERSIST_DIR=./app/memory/chroma_db
MAX_REQUESTS_PER_MINUTE=30
```

---

## 🔧 API Endpoints

```
GET  /health                  Health check
GET  /projects                List projects
POST /projects                Create project
POST /scan                    Scan a repository
POST /chat                    AI chat (any agent)
POST /tasks/generate          AI task generation
GET  /tasks/{project_id}      List tasks
POST /tasks                   Create task
PATCH /tasks/{id}             Update task status
POST /debug/analyze           Analyze error/stacktrace
GET  /debug/{project_id}      Bug history
POST /docs/readme/{id}        Generate README
POST /docs/architecture/{id}  Generate arch doc
GET  /memory/{project_id}     View stored memories
GET  /history/{project_id}    Conversation history
GET  /activity                Activity log
```

---

## 📦 Optional Upgrades

- **Ollama** — Swap Anthropic for local LLMs
- **GitHub API** — PR summaries and repo sync
- **Docker** — Add `Dockerfile` for containerized deployment
- **LangChain** — More complex agent chains
- **Voice** — Add Whisper for voice commands

---

## 📄 License

MIT — use freely, extend liberally.
