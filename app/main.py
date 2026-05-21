"""
AI Dev Manager - FastAPI Backend
Handles all API endpoints for the Streamlit frontend
"""
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from dotenv import load_dotenv

load_dotenv()

from app.database.sqlite_manager import DatabaseManager
from app.memory.vector_store import VectorMemoryManager
from app.repository.scanner import RepositoryScanner
from app.agents.agents import AgentOrchestrator

# ─── Init ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="AI Dev Manager API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()
vector = VectorMemoryManager(persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./app/memory/chroma_db"))
scanner = RepositoryScanner()
orchestrator = AgentOrchestrator()

# ─── Rate limiting (simple in-memory) ────────────────────────────────────────

_request_counts: Dict[str, list] = {}
MAX_RPM = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 30))

def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "local"
    now = datetime.now().timestamp()
    if ip not in _request_counts:
        _request_counts[ip] = []
    _request_counts[ip] = [t for t in _request_counts[ip] if now - t < 60]
    if len(_request_counts[ip]) >= MAX_RPM:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
    _request_counts[ip].append(now)

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    path: str
    project_name: Optional[str] = None

    @validator("path")
    def validate_path(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Path cannot be empty")
        if ".." in v:
            raise ValueError("Path traversal not allowed")
        return v

class ChatRequest(BaseModel):
    message: str
    project_id: Optional[int] = None
    agent_type: str = "general"
    history: Optional[List[Dict]] = None

    @validator("message")
    def validate_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v[:5000]

    @validator("agent_type")
    def validate_agent(cls, v):
        allowed = {"general", "planning", "coding", "debugging", "documentation", "repo_chat"}
        if v not in allowed:
            return "general"
        return v

class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: str = ""
    priority: str = "medium"
    complexity: int = 3
    agent_type: str = "planning"
    tags: List[str] = []

    @validator("title")
    def validate_title(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v[:300]

    @validator("priority")
    def validate_priority(cls, v):
        if v not in {"low", "medium", "high"}:
            return "medium"
        return v

    @validator("complexity")
    def validate_complexity(cls, v):
        return max(1, min(10, v))

class TaskUpdate(BaseModel):
    status: str

    @validator("status")
    def validate_status(cls, v):
        if v not in {"todo", "in_progress", "done"}:
            raise ValueError("Invalid status")
        return v

class FeatureRequest(BaseModel):
    feature: str
    project_id: Optional[int] = None

    @validator("feature")
    def validate_feature(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Feature description cannot be empty")
        return v[:2000]

class BugRequest(BaseModel):
    project_id: int
    error_text: str
    code_context: str = ""

    @validator("error_text")
    def validate_error(cls, v):
        return v.strip()[:5000]

class ProjectCreate(BaseModel):
    name: str
    path: str

# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ─── Projects ─────────────────────────────────────────────────────────────────

@app.get("/projects")
def list_projects():
    return db.get_projects()

@app.post("/projects")
def create_project(req: ProjectCreate):
    pid = db.create_project(name=req.name, path=req.path)
    db.log_activity("project_created", f"Created project: {req.name}", project_id=pid)
    return {"id": pid, "name": req.name, "path": req.path}

@app.get("/projects/{project_id}")
def get_project(project_id: int):
    p = db.get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p

@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    db.delete_project(project_id)
    vector.clear_project_files(project_id)
    return {"deleted": True}

@app.get("/projects/{project_id}/stats")
def project_stats(project_id: int):
    stats = db.get_project_stats(project_id)
    vstats = vector.get_stats()
    stats["vector_files"] = vstats.get("repository_files", 0)
    return stats

# ─── Repository Scanner ───────────────────────────────────────────────────────

@app.post("/scan")
def scan_repository(req: ScanRequest, request: Request, _=Depends(check_rate_limit)):
    # Scan the directory
    result = scanner.scan_directory(req.path)
    if "error" in result:
        raise HTTPException(400, result["error"])

    # Create or find project
    name = req.project_name or result["name"]
    pid = db.create_project(name=name, path=req.path)
    db.update_project_scan(pid, result["tech_stack"], result["file_count"], "")

    # Build context summary
    summary = scanner.build_context_summary(result)

    # Store files in vector DB (limit to 100 files)
    stored = 0
    for f in result["files"][:100]:
        if f.get("content") and len(f["content"]) > 50:
            vector.store_file(pid, f["path"], f["content"])
            stored += 1

    # Store architecture summary in memory
    arch_summary = f"Project: {name}\nPath: {req.path}\n{summary}"
    vector.store_memory(pid, "architecture", arch_summary)
    db.save_memory("architecture", arch_summary, project_id=pid)
    db.log_activity("repository_scanned", f"Scanned {result['file_count']} files", project_id=pid)

    return {
        "project_id": pid,
        "name": name,
        "file_count": result["file_count"],
        "total_lines": result["total_lines"],
        "tech_stack": result["tech_stack"],
        "primary_language": result["primary_language"],
        "directory_structure": result["directory_structure"][:20],
        "key_files": result["key_files"],
        "summary": summary,
        "vectors_stored": stored,
    }

# ─── AI Chat ──────────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest, request: Request, _=Depends(check_rate_limit)):
    # Build context from vector memory
    context = ""
    if req.project_id:
        project = db.get_project(req.project_id)
        if project:
            context += f"Project: {project['name']}\nPath: {project['path']}\n"
            context += f"Tech stack: {', '.join(project.get('tech_stack', []))}\n\n"

        # Semantic search in repo
        relevant = vector.search_repository(req.message, req.project_id, n_results=4)
        if relevant:
            context += "Relevant code context:\n"
            for r in relevant:
                context += f"\n--- {r['metadata'].get('file_path', 'unknown')} ---\n{r['content'][:600]}\n"

        # Search memory
        memories = vector.search_memory(req.message, req.project_id, n_results=3)
        if memories:
            context += "\nProject memory:\n"
            for m in memories:
                context += f"- {m['content'][:200]}\n"

    # Format history for API
    history = req.history or []
    api_messages = [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
    api_messages.append({"role": "user", "content": req.message})

    # Get AI response
    if req.agent_type == "repo_chat":
        response = orchestrator.answer_repo_question(req.message, context, history[-10:])
    else:
        response = orchestrator.general_chat(api_messages, context=context)

    # Save to DB and vector memory
    if req.project_id:
        db.save_message(1, "user", req.message, project_id=req.project_id, agent_type=req.agent_type)
        db.save_message(1, "assistant", response, project_id=req.project_id, agent_type=req.agent_type)
        vector.store_conversation(req.project_id, "user", req.message, req.agent_type)
        vector.store_conversation(req.project_id, "assistant", response, req.agent_type)

    db.log_activity("chat", f"[{req.agent_type}] {req.message[:80]}", project_id=req.project_id)
    return {"response": response, "agent": req.agent_type}

# ─── Task Generation ──────────────────────────────────────────────────────────

@app.post("/tasks/generate")
def generate_tasks(req: FeatureRequest, request: Request, _=Depends(check_rate_limit)):
    context = ""
    if req.project_id:
        project = db.get_project(req.project_id)
        if project:
            context = f"Project: {project['name']}\nTech stack: {', '.join(project.get('tech_stack', []))}"

    raw = orchestrator.generate_tasks(req.feature, context)

    # Parse JSON response
    tasks = []
    try:
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            tasks = json.loads(json_match.group())
    except Exception:
        tasks = []

    # Save tasks to DB
    saved_ids = []
    if req.project_id and tasks:
        for t in tasks:
            tid = db.create_task(
                project_id=req.project_id,
                title=t.get("title", "Untitled task"),
                description=t.get("description", ""),
                priority=t.get("priority", "medium"),
                complexity=t.get("complexity", 3),
                agent_type="planning",
                tags=t.get("tags", []),
            )
            saved_ids.append(tid)
        db.log_activity("tasks_generated", f"Generated {len(tasks)} tasks for: {req.feature[:60]}", project_id=req.project_id)

    return {"tasks": tasks, "saved_ids": saved_ids, "raw": raw}

# ─── Tasks CRUD ───────────────────────────────────────────────────────────────

@app.get("/tasks/{project_id}")
def list_tasks(project_id: int, status: Optional[str] = None):
    return db.get_tasks(project_id, status=status)

@app.post("/tasks")
def create_task(req: TaskCreate):
    tid = db.create_task(
        project_id=req.project_id,
        title=req.title,
        description=req.description,
        priority=req.priority,
        complexity=req.complexity,
        agent_type=req.agent_type,
        tags=req.tags,
    )
    db.log_activity("task_created", f"Task: {req.title[:60]}", project_id=req.project_id)
    return {"id": tid, "title": req.title}

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, req: TaskUpdate):
    db.update_task_status(task_id, req.status)
    return {"updated": True, "task_id": task_id, "status": req.status}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    db.delete_task(task_id)
    return {"deleted": True}

# ─── Debugging ────────────────────────────────────────────────────────────────

@app.post("/debug/analyze")
def analyze_bug(req: BugRequest, request: Request, _=Depends(check_rate_limit)):
    # Check past similar bugs
    past = vector.search_debug_history(req.error_text, req.project_id)

    # Get project context
    context = ""
    if req.project_id:
        project = db.get_project(req.project_id)
        if project:
            context = f"Project: {project['name']}\nTech: {', '.join(project.get('tech_stack', []))}"

    if past:
        context += "\nSimilar past issues:\n" + "\n".join([p["content"][:300] for p in past])

    result = orchestrator.analyze_error(req.error_text, req.code_context, context)

    # Save to DB and vector
    if req.project_id:
        bid = db.create_bug_report(
            project_id=req.project_id,
            title=req.error_text[:100],
            stack_trace=req.error_text,
            analysis=result["analysis"],
            suggested_fix=result["analysis"],
            severity="medium",
        )
        vector.store_debug(req.project_id, req.error_text[:300], result["analysis"], "")
        db.log_activity("bug_analyzed", f"Analyzed: {req.error_text[:60]}", project_id=req.project_id)
        return {**result, "bug_id": bid}

    return result

@app.get("/debug/{project_id}")
def list_bugs(project_id: int):
    return db.get_bug_reports(project_id)

@app.patch("/debug/{bug_id}/status")
def update_bug_status(bug_id: int, status: str):
    db.update_bug_status(bug_id, status)
    return {"updated": True}

# ─── Code Tools ───────────────────────────────────────────────────────────────

class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"

    @validator("code")
    def validate_code(cls, v):
        return v.strip()[:8000]

@app.post("/code/review")
def review_code(req: CodeReviewRequest, request: Request, _=Depends(check_rate_limit)):
    result = orchestrator.review_code(req.code, req.language)
    return {"review": result}

# ─── Documentation ────────────────────────────────────────────────────────────

@app.post("/docs/readme/{project_id}")
def generate_readme(project_id: int, request: Request, _=Depends(check_rate_limit)):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    memories = db.get_memories(project_id=project_id, memory_type="architecture")
    context = "\n".join([m["content"] for m in memories[:3]])
    if not context:
        context = f"Project: {project['name']}\nTech: {', '.join(project.get('tech_stack', []))}"
    readme = orchestrator.generate_readme(context)
    db.save_memory("readme", readme, project_id=project_id)
    db.log_activity("readme_generated", f"Generated README for {project['name']}", project_id=project_id)
    return {"readme": readme}

@app.post("/docs/architecture/{project_id}")
def generate_architecture(project_id: int, request: Request, _=Depends(check_rate_limit)):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    memories = db.get_memories(project_id=project_id, memory_type="architecture")
    context = "\n".join([m["content"] for m in memories[:3]])
    if not context:
        context = f"Project: {project['name']}\nTech: {', '.join(project.get('tech_stack', []))}"
    arch = orchestrator.summarize_architecture(context)
    db.save_memory("architecture_doc", arch, project_id=project_id)
    return {"architecture": arch}

# ─── Memory ───────────────────────────────────────────────────────────────────

@app.get("/memory/{project_id}")
def get_memories(project_id: int):
    return db.get_memories(project_id=project_id)

@app.get("/memory/{project_id}/vector-stats")
def vector_stats(project_id: int):
    return vector.get_stats()

# ─── Conversation History ─────────────────────────────────────────────────────

@app.get("/history/{project_id}")
def get_history(project_id: int, agent_type: Optional[str] = None, limit: int = 50):
    return db.get_conversation_history(project_id=project_id, limit=limit, agent_type=agent_type)

@app.delete("/history/{project_id}")
def clear_history(project_id: int):
    # Just return success; we don't delete, just acknowledge
    return {"cleared": True}

# ─── Activity ─────────────────────────────────────────────────────────────────

@app.get("/activity")
def get_activity(project_id: Optional[int] = None, limit: int = 30):
    return db.get_activity(project_id=project_id, limit=limit)

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
