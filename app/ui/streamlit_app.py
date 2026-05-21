"""
AI Dev Manager - Streamlit Frontend
A local-first AI engineering manager for developers.
"""
import streamlit as st
import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Dev Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600;700&display=swap');

/* Base theme overrides */
:root {
    --bg-primary: #0d0d0f;
    --bg-secondary: #141416;
    --bg-card: #1a1a1f;
    --bg-hover: #22222a;
    --border: #2a2a35;
    --accent: #7c6af7;
    --accent-dim: #5548c8;
    --accent-glow: rgba(124, 106, 247, 0.15);
    --text-primary: #e8e8f0;
    --text-secondary: #8888aa;
    --text-muted: #555570;
    --green: #4ade80;
    --yellow: #fbbf24;
    --red: #f87171;
    --blue: #60a5fa;
    --orange: #fb923c;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

/* Headings */
h1, h2, h3 { font-family: 'Inter', sans-serif !important; font-weight: 600 !important; }
h1 { color: var(--text-primary) !important; letter-spacing: -0.5px; }
h2 { color: var(--text-primary) !important; font-size: 1.1rem !important; }
h3 { color: var(--text-secondary) !important; font-size: 0.9rem !important; font-weight: 500 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}
[data-testid="stMetricValue"] { color: var(--text-primary) !important; font-weight: 600 !important; }
[data-testid="stMetricLabel"] { color: var(--text-secondary) !important; font-size: 0.75rem !important; }

/* Buttons */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: var(--accent-dim) !important;
    box-shadow: 0 0 20px var(--accent-glow) !important;
}

/* Text inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

/* Chat messages */
.chat-user {
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    margin-left: 60px;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text-primary);
}
.chat-assistant {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px 12px 12px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    margin-right: 20px;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text-primary);
}
.chat-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.chat-label.user { color: var(--text-muted); }
.chat-label.assistant { color: var(--accent); }

/* Code blocks */
code {
    background: rgba(124,106,247,0.1) !important;
    color: var(--accent) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82em !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
}

/* Task cards */
.task-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    transition: border-color 0.15s;
}
.task-card:hover { border-color: var(--accent); }
.task-title { font-weight: 500; font-size: 0.88rem; color: var(--text-primary); }
.task-meta { font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px; }

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-todo { background: rgba(85,85,112,0.3); color: var(--text-secondary); }
.badge-in_progress { background: rgba(251,191,36,0.15); color: var(--yellow); }
.badge-done { background: rgba(74,222,128,0.15); color: var(--green); }
.badge-high { background: rgba(248,113,113,0.15); color: var(--red); }
.badge-medium { background: rgba(251,191,36,0.15); color: var(--yellow); }
.badge-low { background: rgba(96,165,250,0.15); color: var(--blue); }
.badge-open { background: rgba(248,113,113,0.15); color: var(--red); }
.badge-resolved { background: rgba(74,222,128,0.15); color: var(--green); }

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    padding: 12px 0 6px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
}

/* Tech stack pills */
.tech-pill {
    display: inline-block;
    background: var(--accent-glow);
    border: 1px solid rgba(124,106,247,0.3);
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    margin: 2px 3px;
    font-family: 'JetBrains Mono', monospace;
}

/* Alert boxes */
.alert-info {
    background: rgba(96,165,250,0.1);
    border: 1px solid rgba(96,165,250,0.3);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.84rem;
    color: var(--blue);
    margin: 8px 0;
}
.alert-success {
    background: rgba(74,222,128,0.1);
    border: 1px solid rgba(74,222,128,0.3);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.84rem;
    color: var(--green);
    margin: 8px 0;
}
.alert-error {
    background: rgba(248,113,113,0.1);
    border: 1px solid rgba(248,113,113,0.3);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.84rem;
    color: var(--red);
    margin: 8px 0;
}

/* Dividers */
hr { border-color: var(--border) !important; margin: 16px 0 !important; }

/* Expanders */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* Selectbox */
.stSelectbox > div > div > div {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Number input */
.stNumberInput input {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* Sidebar logo area */
.logo-area {
    padding: 8px 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}
.logo-text {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.3px;
}
.logo-sub {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 2px;
}

/* File tree */
.file-item {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-secondary);
    padding: 2px 0;
}

/* Spinner override */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* Agent label */
.agent-badge {
    display: inline-block;
    background: var(--accent-glow);
    border: 1px solid rgba(124,106,247,0.3);
    color: var(--accent);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
}

/* Memory card */
.memory-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--blue);
    border-radius: 4px 8px 8px 4px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def api(method: str, endpoint: str, **kwargs):
    """Make API request with error handling."""
    try:
        r = getattr(requests, method)(f"{API_BASE}{endpoint}", timeout=120, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⚡ API server not running. Start it with: `python run.py --api`")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def check_api():
    """Check if the API server is reachable."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def badge(text: str, kind: str = "") -> str:
    return f'<span class="badge badge-{kind or text.lower().replace(" ", "_")}">{text}</span>'

def priority_icon(p: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p, "⚪")

def format_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace(" ", "T").split(".")[0])
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return ts[:16] if ts else ""

# ─── Session State ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "project_id": None,
        "project_name": None,
        "chat_history": [],
        "agent_type": "general",
        "page": "Dashboard",
        "api_ok": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="logo-area">
        <div class="logo-text">⚡ AI Dev Manager</div>
        <div class="logo-sub">Local-first AI engineering assistant</div>
    </div>
    """, unsafe_allow_html=True)

    # API status
    api_ok = check_api()
    if api_ok:
        st.markdown('<div class="alert-success">● API Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-error">● API Offline — run: python run.py</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Navigation</div>', unsafe_allow_html=True)

    pages = {
        "🏠 Dashboard": "Dashboard",
        "📁 Repository": "Repository",
        "💬 AI Chat": "Chat",
        "✅ Tasks": "Tasks",
        "🐛 Debugger": "Debugger",
        "🧠 Memory": "Memory",
        "🤖 Agents": "Agents",
    }
    for label, page_key in pages.items():
        if st.button(label, key=f"nav_{page_key}", use_container_width=True):
            st.session_state.page = page_key
            st.rerun()

    st.markdown('<div class="section-header">Active Project</div>', unsafe_allow_html=True)

    if api_ok:
        projects = api("get", "/projects") or []
        project_options = {f"{p['name']} (#{p['id']})": p for p in projects}
        if project_options:
            sel = st.selectbox(
                "Select Project",
                options=["— none —"] + list(project_options.keys()),
                label_visibility="collapsed",
            )
            if sel != "— none —" and sel in project_options:
                p = project_options[sel]
                st.session_state.project_id = p["id"]
                st.session_state.project_name = p["name"]
                st.markdown(f'<div class="file-item">📍 {p["path"][:40]}</div>', unsafe_allow_html=True)
                tech = p.get("tech_stack") or []
                if tech:
                    pills = "".join(f'<span class="tech-pill">{t}</span>' for t in tech[:6])
                    st.markdown(pills, unsafe_allow_html=True)
            else:
                st.session_state.project_id = None
                st.session_state.project_name = None
        else:
            st.markdown('<div class="alert-info">No projects yet. Scan a repo first.</div>', unsafe_allow_html=True)

    # Agent picker
    st.markdown('<div class="section-header">Active Agent</div>', unsafe_allow_html=True)
    agent_map = {
        "🧠 General": "general",
        "📋 Planning": "planning",
        "💻 Coding": "coding",
        "🔍 Repo Chat": "repo_chat",
        "📝 Documentation": "documentation",
    }
    agent_sel = st.selectbox(
        "Agent",
        list(agent_map.keys()),
        label_visibility="collapsed",
    )
    st.session_state.agent_type = agent_map[agent_sel]

    # Clear chat
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ─── Pages ────────────────────────────────────────────────────────────────────

page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown("## ⚡ Dashboard")

    if not api_ok:
        st.markdown("""
        <div class="alert-error">
        <b>API server is not running.</b><br>
        Start the backend: <code>python run.py</code>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    pid = st.session_state.project_id

    if pid:
        stats = api("get", f"/projects/{pid}/stats") or {}
        pinfo = api("get", f"/projects/{pid}") or {}

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.metric("📂 Files", pinfo.get("file_count", 0))
        with col2: st.metric("✅ Done", stats.get("done", 0))
        with col3: st.metric("🔄 In Progress", stats.get("in_progress", 0))
        with col4: st.metric("📌 Todo", stats.get("todo", 0))
        with col5: st.metric("🐛 Open Bugs", stats.get("open_bugs", 0))

        st.markdown("---")
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("### Recent Activity")
            activity = api("get", f"/activity?project_id={pid}&limit=15") or []
            if activity:
                for act in activity:
                    st.markdown(
                        f'<div class="task-card"><span class="task-title">{act["action"].replace("_", " ").title()}</span>'
                        f'<div class="task-meta">{act.get("detail", "")[:80]} · {format_time(act["time"])}</div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="alert-info">No activity yet.</div>', unsafe_allow_html=True)

        with col_right:
            st.markdown("### Quick Actions")
            if st.button("🔍 Scan Repository", use_container_width=True):
                st.session_state.page = "Repository"
                st.rerun()
            if st.button("💬 Open AI Chat", use_container_width=True):
                st.session_state.page = "Chat"
                st.rerun()
            if st.button("➕ Generate Tasks", use_container_width=True):
                st.session_state.page = "Tasks"
                st.rerun()
            if st.button("🐛 Debug Error", use_container_width=True):
                st.session_state.page = "Debugger"
                st.rerun()

            st.markdown("### Tech Stack")
            tech = pinfo.get("tech_stack") or []
            if tech:
                pills = "".join(f'<span class="tech-pill">{t}</span>' for t in tech)
                st.markdown(pills, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-info">
        👆 Select a project from the sidebar, or scan a repository to get started.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### ⚡ Getting Started")
        st.markdown("""
        1. **Scan a Repository** — Point AI Dev Manager at your local codebase
        2. **Chat with AI** — Ask questions about your code, architecture, and more
        3. **Generate Tasks** — Describe a feature and get a full task breakdown
        4. **Debug Errors** — Paste stack traces for instant AI analysis
        5. **Track Progress** — Manage tasks and bugs across your project
        """)

        # Show all projects
        projects = api("get", "/projects") or []
        if projects:
            st.markdown("### Your Projects")
            for p in projects:
                col1, col2 = st.columns([4, 1])
                with col1:
                    tech_str = ", ".join((p.get("tech_stack") or [])[:4])
                    st.markdown(
                        f'<div class="task-card"><span class="task-title">📁 {p["name"]}</span>'
                        f'<div class="task-meta">{p["path"][:60]} · {tech_str}</div></div>',
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("Select", key=f"sel_{p['id']}"):
                        st.session_state.project_id = p["id"]
                        st.session_state.project_name = p["name"]
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Repository":
    st.markdown("## 📁 Repository Scanner")

    col1, col2 = st.columns([3, 1])
    with col1:
        repo_path = st.text_input("Repository path", placeholder="/home/user/my-project", key="repo_path_input")
    with col2:
        repo_name = st.text_input("Project name (optional)", placeholder="my-project")

    col_scan, col_del = st.columns([1, 4])
    with col_scan:
        scan_btn = st.button("🔍 Scan Repository", use_container_width=True)

    if scan_btn and repo_path:
        if ".." in repo_path:
            st.error("Invalid path.")
        else:
            with st.spinner("Scanning repository…"):
                result = api("post", "/scan", json={"path": repo_path, "project_name": repo_name or None})
            if result:
                st.session_state.project_id = result["project_id"]
                st.session_state.project_name = result["name"]
                st.success(f"✅ Scanned **{result['name']}** — {result['file_count']} files, {result['total_lines']:,} lines")

                col_a, col_b, col_c = st.columns(3)
                with col_a: st.metric("Files", result["file_count"])
                with col_b: st.metric("Lines", f"{result['total_lines']:,}")
                with col_c: st.metric("Vectors", result["vectors_stored"])

                st.markdown("### Tech Stack Detected")
                tech_str = "".join(f'<span class="tech-pill">{t}</span>' for t in result["tech_stack"])
                st.markdown(tech_str, unsafe_allow_html=True)

                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown("### Directory Structure")
                    for line in result["directory_structure"]:
                        st.markdown(f'<div class="file-item">{line}</div>', unsafe_allow_html=True)
                with col_r:
                    st.markdown("### Key Files")
                    for f in result["key_files"]:
                        st.markdown(f'<div class="file-item">📄 {f}</div>', unsafe_allow_html=True)

                with st.expander("📋 Full Summary"):
                    st.text(result["summary"])

    # Existing projects
    st.markdown("---")
    st.markdown("### Scanned Projects")
    projects = api("get", "/projects") or []
    for p in projects:
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            tech_str = ", ".join((p.get("tech_stack") or [])[:5]) or "—"
            st.markdown(
                f'<div class="task-card"><span class="task-title">📁 {p["name"]}</span>'
                f'<div class="task-meta">{p["path"][:60]}</div>'
                f'<div class="task-meta">{tech_str} · {p["file_count"]} files · Scanned: {format_time(p.get("last_scanned","") or "")}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Select", key=f"repo_sel_{p['id']}"):
                st.session_state.project_id = p["id"]
                st.session_state.project_name = p["name"]
                st.rerun()
        with col3:
            if st.button("🗑", key=f"repo_del_{p['id']}"):
                api("delete", f"/projects/{p['id']}")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Chat":
    pid = st.session_state.project_id
    agent = st.session_state.agent_type
    agent_labels = {
        "general": "General AI", "planning": "Planning Agent",
        "coding": "Coding Agent", "repo_chat": "Repo Chat",
        "documentation": "Docs Agent", "debugging": "Debug Agent",
    }

    st.markdown(f"## 💬 AI Chat <span class='agent-badge'>{agent_labels.get(agent, agent)}</span>", unsafe_allow_html=True)
    if pid:
        st.markdown(f'<div class="alert-info">📁 Context: <b>{st.session_state.project_name}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-info">💡 Select a project for context-aware chat.</div>', unsafe_allow_html=True)

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-label user">You</div><div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                agent_lbl = agent_labels.get(msg.get("agent", "general"), "AI")
                st.markdown(f'<div class="chat-label assistant">{agent_lbl}</div><div class="chat-assistant">', unsafe_allow_html=True)
                st.markdown(msg["content"])
                st.markdown('</div>', unsafe_allow_html=True)

    # Input
    st.markdown("---")
    
    # Quick prompts
    quick_prompts = {
        "general": ["Summarize this project", "What are the main components?", "What can be improved?"],
        "repo_chat": ["Explain the architecture", "How does authentication work?", "Find security risks"],
        "planning": ["Create tasks for user auth", "Plan a REST API feature", "Sprint planning for MVP"],
        "coding": ["Review the main file", "Suggest refactoring", "Add error handling"],
        "documentation": ["Generate README", "Document the API", "Summarize architecture"],
        "debugging": ["Check for common bugs", "Analyze error handling", "Find risky code"],
    }
    prompts = quick_prompts.get(agent, [])
    if prompts:
        cols = st.columns(len(prompts))
        for i, p in enumerate(prompts):
            with cols[i]:
                if st.button(p, key=f"qp_{i}", use_container_width=True):
                    st.session_state._quick_prompt = p

    user_input = st.text_input(
        "Message",
        placeholder=f"Ask the {agent_labels.get(agent, 'AI')}…",
        key="chat_input",
        label_visibility="collapsed",
    )

    send = st.button("Send ↵", use_container_width=False)

    # Handle quick prompt
    if hasattr(st.session_state, "_quick_prompt"):
        user_input = st.session_state._quick_prompt
        del st.session_state._quick_prompt
        send = True

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Thinking…"):
            result = api("post", "/chat", json={
                "message": user_input,
                "project_id": pid,
                "agent_type": agent,
                "history": [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[-10:]],
            })
        if result:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["response"],
                "agent": result.get("agent", agent),
            })
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Tasks":
    pid = st.session_state.project_id
    st.markdown("## ✅ Task Manager")

    if not pid:
        st.markdown('<div class="alert-error">Select a project to manage tasks.</div>', unsafe_allow_html=True)
        st.stop()

    # Generate tasks
    with st.expander("🤖 AI Task Generator", expanded=True):
        feature_desc = st.text_area(
            "Describe a feature or epic",
            placeholder="e.g., Add user authentication with JWT, email verification, and password reset",
            height=80,
        )
        if st.button("⚡ Generate Tasks with AI", use_container_width=True) and feature_desc.strip():
            with st.spinner("Planning tasks…"):
                result = api("post", "/tasks/generate", json={"feature": feature_desc, "project_id": pid})
            if result:
                tasks = result.get("tasks", [])
                if tasks:
                    st.success(f"✅ Generated {len(tasks)} tasks!")
                    for t in tasks:
                        st.markdown(
                            f'<div class="task-card">'
                            f'<span class="task-title">{priority_icon(t.get("priority","medium"))} {t.get("title","")}</span>'
                            f'<div class="task-meta">{t.get("description","")[:120]}</div>'
                            f'<div class="task-meta" style="margin-top:4px">'
                            f'{badge(t.get("priority","medium"),"priority_"+t.get("priority","medium"))} '
                            f'Complexity: {t.get("complexity",3)}/10</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    st.rerun()
                else:
                    st.warning("Could not parse tasks. Raw response:")
                    st.text(result.get("raw", "")[:1000])

    # Manual task creation
    with st.expander("➕ Add Task Manually"):
        col1, col2 = st.columns(2)
        with col1:
            t_title = st.text_input("Title", key="new_task_title")
            t_desc = st.text_area("Description", height=60, key="new_task_desc")
        with col2:
            t_priority = st.selectbox("Priority", ["medium", "high", "low"], key="new_task_priority")
            t_complexity = st.number_input("Complexity (1-10)", min_value=1, max_value=10, value=3, key="new_task_complexity")
        if st.button("Add Task", use_container_width=True) and t_title.strip():
            api("post", "/tasks", json={
                "project_id": pid, "title": t_title, "description": t_desc,
                "priority": t_priority, "complexity": t_complexity,
            })
            st.rerun()

    st.markdown("---")

    # Task board
    tasks = api("get", f"/tasks/{pid}") or []
    cols = {"todo": [], "in_progress": [], "done": []}
    for t in tasks:
        status = t.get("status", "todo")
        if status in cols:
            cols[status].append(t)

    col1, col2, col3 = st.columns(3)

    def render_task_column(tasks_list, col, label, status_color):
        with col:
            st.markdown(f'<div class="section-header">{label} ({len(tasks_list)})</div>', unsafe_allow_html=True)
            for t in tasks_list:
                with st.container():
                    st.markdown(
                        f'<div class="task-card">'
                        f'<span class="task-title">{priority_icon(t.get("priority","medium"))} {t["title"]}</span>'
                        f'<div class="task-meta">{t.get("description","")[:80]}</div>'
                        f'<div class="task-meta" style="margin-top:4px">'
                        f'{badge(t.get("priority","medium"))} · {t.get("complexity",3)}/10 · {format_time(t["created_at"])}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if t["status"] != "todo" and st.button("📌", key=f"todo_{t['id']}", help="Move to Todo"):
                            api("patch", f"/tasks/{t['id']}", json={"status": "todo"})
                            st.rerun()
                    with c2:
                        if t["status"] != "in_progress" and st.button("🔄", key=f"wip_{t['id']}", help="In Progress"):
                            api("patch", f"/tasks/{t['id']}", json={"status": "in_progress"})
                            st.rerun()
                    with c3:
                        if t["status"] != "done" and st.button("✅", key=f"done_{t['id']}", help="Mark Done"):
                            api("patch", f"/tasks/{t['id']}", json={"status": "done"})
                            st.rerun()
                    with c4:
                        if st.button("🗑", key=f"del_{t['id']}", help="Delete"):
                            api("delete", f"/tasks/{t['id']}")
                            st.rerun()

    render_task_column(cols["todo"], col1, "📌 Todo", "var(--text-muted)")
    render_task_column(cols["in_progress"], col2, "🔄 In Progress", "var(--yellow)")
    render_task_column(cols["done"], col3, "✅ Done", "var(--green)")

# ══════════════════════════════════════════════════════════════════════════════
# DEBUGGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Debugger":
    pid = st.session_state.project_id
    st.markdown("## 🐛 Debugging Assistant")

    tab1, tab2 = st.tabs(["🔍 Analyze Error", "📋 Bug History"])

    with tab1:
        error_input = st.text_area(
            "Paste your error / stack trace",
            placeholder="Traceback (most recent call last):\n  File ...\nAttributeError: 'NoneType' object has no attribute 'execute'",
            height=150,
        )
        code_ctx = st.text_area(
            "Code context (optional)",
            placeholder="Paste the relevant code around the error…",
            height=100,
        )

        if st.button("🤖 Analyze with AI", use_container_width=True) and error_input.strip():
            if not pid:
                st.warning("No project selected — analysis will work but won't be saved.")
            with st.spinner("Analyzing error…"):
                result = api("post", "/debug/analyze", json={
                    "project_id": pid or 0,
                    "error_text": error_input,
                    "code_context": code_ctx,
                })
            if result:
                st.markdown("### 🔍 Analysis")
                st.markdown(result["analysis"])
                if "bug_id" in result:
                    st.markdown(f'<div class="alert-success">✅ Bug saved with ID #{result["bug_id"]}</div>', unsafe_allow_html=True)

    with tab2:
        if not pid:
            st.markdown('<div class="alert-error">Select a project to view bug history.</div>', unsafe_allow_html=True)
        else:
            bugs = api("get", f"/debug/{pid}") or []
            if not bugs:
                st.markdown('<div class="alert-info">No bugs reported yet.</div>', unsafe_allow_html=True)
            for b in bugs:
                sev_color = {"critical": "var(--red)", "high": "var(--red)", "medium": "var(--yellow)", "low": "var(--blue)"}.get(b.get("severity", "medium"), "var(--yellow)")
                with st.expander(f"{'🔴' if b['status']=='open' else '✅'} {b['title'][:80]}"):
                    st.markdown(f"**Severity:** {b.get('severity','medium').title()} | **Status:** {b['status'].title()} | **Reported:** {format_time(b['created_at'])}")
                    if b.get("stack_trace"):
                        st.code(b["stack_trace"][:1000], language="text")
                    st.markdown("**Analysis:**")
                    st.markdown(b.get("analysis", "—")[:2000])
                    col1, col2 = st.columns(2)
                    with col1:
                        if b["status"] == "open" and st.button("✅ Mark Resolved", key=f"res_{b['id']}"):
                            api("patch", f"/debug/{b['id']}/status?status=resolved")
                            st.rerun()
                    with col2:
                        if b["status"] == "open" and st.button("🚫 Ignore", key=f"ign_{b['id']}"):
                            api("patch", f"/debug/{b['id']}/status?status=ignored")
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MEMORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Memory":
    pid = st.session_state.project_id
    st.markdown("## 🧠 Project Memory")

    vstats = api("get", f"/memory/{pid or 0}/vector-stats") if pid else {}
    if vstats:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("📂 Repo Files", vstats.get("repository_files", 0))
        with col2: st.metric("🧠 Memories", vstats.get("memories", 0))
        with col3: st.metric("💬 Conversations", vstats.get("conversations", 0))
        with col4: st.metric("🐛 Debug Entries", vstats.get("debug_entries", 0))

    if not pid:
        st.markdown('<div class="alert-error">Select a project to view memory.</div>', unsafe_allow_html=True)
        st.stop()

    memories = api("get", f"/memory/{pid}") or []
    if not memories:
        st.markdown('<div class="alert-info">No memory stored yet. Scan a repository or chat with the AI to build memory.</div>', unsafe_allow_html=True)
    else:
        type_filter = st.selectbox("Filter by type", ["all"] + list({m["type"] for m in memories}))
        shown = memories if type_filter == "all" else [m for m in memories if m["type"] == type_filter]
        st.markdown(f"Showing {len(shown)} memory entries")
        for m in shown[:30]:
            st.markdown(
                f'<div class="memory-card">'
                f'<span style="font-size:0.7rem;font-weight:600;text-transform:uppercase;color:var(--blue)">{m["type"]}</span>'
                f' <span style="font-size:0.7rem;color:var(--text-muted)">{format_time(m["created_at"])}</span>'
                f'<div style="margin-top:6px">{m["content"][:300]}{"…" if len(m["content"])>300 else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Conversation history
    st.markdown("---")
    st.markdown("### 💬 Conversation History")
    history = api("get", f"/history/{pid}?limit=30") or []
    if not history:
        st.markdown('<div class="alert-info">No conversations yet.</div>', unsafe_allow_html=True)
    else:
        for msg in history:
            role = msg["role"]
            content = msg["content"][:300]
            agent = msg.get("agent", "general")
            if role == "user":
                st.markdown(f'<div class="chat-label user">You · {format_time(msg["time"])}</div><div class="chat-user">{content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-label assistant">{agent} · {format_time(msg["time"])}</div><div class="chat-assistant">{content}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Agents":
    pid = st.session_state.project_id
    st.markdown("## 🤖 AI Agent Panel")

    agent_cards = [
        ("🧠", "General Agent", "general", "Handles open-ended questions, analysis, and developer Q&A."),
        ("📋", "Planning Agent", "planning", "Breaks features into tasks, estimates complexity, plans sprints."),
        ("💻", "Coding Agent", "coding", "Writes code, reviews implementations, suggests refactors."),
        ("🔍", "Repo Chat Agent", "repo_chat", "Answers questions about your codebase using RAG."),
        ("📝", "Documentation Agent", "documentation", "Generates README, architecture docs, API documentation."),
        ("🐛", "Debugging Agent", "debugging", "Analyzes errors, explains bugs, provides fixes."),
    ]

    for icon, name, key, desc in agent_cards:
        with st.expander(f"{icon} {name}"):
            st.markdown(f'<div class="task-meta">{desc}</div>', unsafe_allow_html=True)
            task_input = st.text_area(f"Task for {name}", height=80, key=f"agent_task_{key}",
                                       placeholder=f"What do you want the {name} to do?")
            if st.button(f"Run {name}", key=f"agent_run_{key}", use_container_width=True) and task_input.strip():
                with st.spinner(f"{name} working…"):
                    result = api("post", "/chat", json={
                        "message": task_input,
                        "project_id": pid,
                        "agent_type": key,
                        "history": [],
                    })
                if result:
                    st.markdown("**Output:**")
                    st.markdown(result["response"])

    # Special: Generate README / Architecture
    st.markdown("---")
    st.markdown("### 📄 One-Click Documentation")

    if pid:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📖 Generate README.md", use_container_width=True):
                with st.spinner("Writing README…"):
                    result = api("post", f"/docs/readme/{pid}")
                if result:
                    st.markdown("### README.md Preview")
                    st.markdown(result["readme"])
                    # Download
                    st.download_button("⬇️ Download README.md", data=result["readme"],
                                       file_name="README.md", mime="text/markdown")
        with col2:
            if st.button("🏗 Generate Architecture Doc", use_container_width=True):
                with st.spinner("Analyzing architecture…"):
                    result = api("post", f"/docs/architecture/{pid}")
                if result:
                    st.markdown("### Architecture Summary")
                    st.markdown(result["architecture"])
    else:
        st.markdown('<div class="alert-error">Select a project to use documentation tools.</div>', unsafe_allow_html=True)

    # Code review
    st.markdown("---")
    st.markdown("### 🔎 Code Review")
    code_to_review = st.text_area("Paste code to review", height=120, placeholder="Paste any code snippet here…")
    lang = st.selectbox("Language", ["python", "javascript", "typescript", "java", "go", "rust", "other"])
    if st.button("🤖 Review Code", use_container_width=True) and code_to_review.strip():
        with st.spinner("Reviewing…"):
            result = api("post", "/code/review", json={"code": code_to_review, "language": lang})
        if result:
            st.markdown("### Review")
            st.markdown(result["review"])
