"""
SQLite Database Manager - handles all local database operations
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Boolean, Float, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.sql import func
import hashlib
import secrets

Base = declarative_base()

# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    projects = relationship("Project", back_populates="owner")
    conversations = relationship("Conversation", back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    path = Column(String(500), nullable=False)
    description = Column(Text, default="")
    tech_stack = Column(JSON, default=list)
    file_count = Column(Integer, default=0)
    last_scanned = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")
    conversations = relationship("Conversation", back_populates="project")
    bug_reports = relationship("BugReport", back_populates="project")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    agent_type = Column(String(50), default="general")
    created_at = Column(DateTime, default=func.now())
    project = relationship("Project", back_populates="conversations")
    user = relationship("User", back_populates="conversations")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    status = Column(String(30), default="todo")  # todo / in_progress / done
    priority = Column(String(20), default="medium")  # low / medium / high
    complexity = Column(Integer, default=3)  # 1-10
    agent_type = Column(String(50), default="planning")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    due_date = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    project = relationship("Project", back_populates="tasks")


class BugReport(Base):
    __tablename__ = "bug_reports"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String(300), nullable=False)
    stack_trace = Column(Text, default="")
    analysis = Column(Text, default="")
    suggested_fix = Column(Text, default="")
    severity = Column(String(20), default="medium")
    status = Column(String(30), default="open")  # open / resolved / ignored
    created_at = Column(DateTime, default=func.now())
    project = relationship("Project", back_populates="bug_reports")


class MemoryLog(Base):
    __tablename__ = "memory_logs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    memory_type = Column(String(50), nullable=False)  # architecture / summary / insight
    content = Column(Text, nullable=False)
    vector_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())


# ─── Database Manager ─────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_path = Path(__file__).parent / "app.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self._ensure_default_user()

    def get_session(self) -> Session:
        return self.SessionLocal()

    def _hash_password(self, password: str) -> str:
        salt = "ai_dev_manager_salt"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def _ensure_default_user(self):
        with self.get_session() as session:
            user = session.query(User).filter_by(username="dev").first()
            if not user:
                user = User(
                    username="dev",
                    email="dev@local.ai",
                    password_hash=self._hash_password("dev123")
                )
                session.add(user)
                session.commit()

    # ── Users ──────────────────────────────────────────────────────────────

    def get_user(self, username: str) -> Optional[User]:
        with self.get_session() as session:
            return session.query(User).filter_by(username=username).first()

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        with self.get_session() as session:
            user = session.query(User).filter_by(username=username).first()
            if user and user.password_hash == self._hash_password(password):
                return {"id": user.id, "username": user.username, "email": user.email}
        return None

    # ── Projects ────────────────────────────────────────────────────────────

    def create_project(self, name: str, path: str, owner_id: int = 1, description: str = "") -> int:
        with self.get_session() as session:
            p = Project(name=name, path=path, owner_id=owner_id, description=description)
            session.add(p)
            session.commit()
            session.refresh(p)
            return p.id

    def update_project_scan(self, project_id: int, tech_stack: list, file_count: int, description: str):
        with self.get_session() as session:
            p = session.query(Project).filter_by(id=project_id).first()
            if p:
                p.tech_stack = tech_stack
                p.file_count = file_count
                p.description = description
                p.last_scanned = datetime.now()
                session.commit()

    def get_projects(self, owner_id: int = 1) -> List[Dict]:
        with self.get_session() as session:
            projects = session.query(Project).filter_by(owner_id=owner_id).all()
            return [
                {
                    "id": p.id, "name": p.name, "path": p.path,
                    "description": p.description, "tech_stack": p.tech_stack or [],
                    "file_count": p.file_count, "last_scanned": str(p.last_scanned) if p.last_scanned else None,
                    "created_at": str(p.created_at)
                }
                for p in projects
            ]

    def get_project(self, project_id: int) -> Optional[Dict]:
        with self.get_session() as session:
            p = session.query(Project).filter_by(id=project_id).first()
            if not p:
                return None
            return {
                "id": p.id, "name": p.name, "path": p.path,
                "description": p.description, "tech_stack": p.tech_stack or [],
                "file_count": p.file_count, "last_scanned": str(p.last_scanned) if p.last_scanned else None,
                "created_at": str(p.created_at)
            }

    def delete_project(self, project_id: int):
        with self.get_session() as session:
            p = session.query(Project).filter_by(id=project_id).first()
            if p:
                session.delete(p)
                session.commit()

    # ── Conversations ────────────────────────────────────────────────────────

    def save_message(self, user_id: int, role: str, content: str,
                     project_id: int = None, agent_type: str = "general"):
        with self.get_session() as session:
            msg = Conversation(
                user_id=user_id, role=role, content=content,
                project_id=project_id, agent_type=agent_type
            )
            session.add(msg)
            session.commit()

    def get_conversation_history(self, project_id: int = None, limit: int = 50, agent_type: str = None) -> List[Dict]:
        with self.get_session() as session:
            q = session.query(Conversation)
            if project_id:
                q = q.filter_by(project_id=project_id)
            if agent_type:
                q = q.filter_by(agent_type=agent_type)
            msgs = q.order_by(Conversation.created_at.desc()).limit(limit).all()
            return [{"role": m.role, "content": m.content, "agent": m.agent_type, "time": str(m.created_at)} for m in reversed(msgs)]

    # ── Tasks ────────────────────────────────────────────────────────────────

    def create_task(self, project_id: int, title: str, description: str = "",
                    priority: str = "medium", complexity: int = 3,
                    agent_type: str = "planning", tags: list = None) -> int:
        with self.get_session() as session:
            t = Task(
                project_id=project_id, title=title, description=description,
                priority=priority, complexity=complexity, agent_type=agent_type,
                tags=tags or []
            )
            session.add(t)
            session.commit()
            session.refresh(t)
            return t.id

    def get_tasks(self, project_id: int, status: str = None) -> List[Dict]:
        with self.get_session() as session:
            q = session.query(Task).filter_by(project_id=project_id)
            if status:
                q = q.filter_by(status=status)
            tasks = q.order_by(Task.created_at.desc()).all()
            return [
                {
                    "id": t.id, "title": t.title, "description": t.description,
                    "status": t.status, "priority": t.priority, "complexity": t.complexity,
                    "agent_type": t.agent_type, "tags": t.tags or [],
                    "created_at": str(t.created_at), "updated_at": str(t.updated_at)
                }
                for t in tasks
            ]

    def update_task_status(self, task_id: int, status: str):
        with self.get_session() as session:
            t = session.query(Task).filter_by(id=task_id).first()
            if t:
                t.status = status
                t.updated_at = datetime.now()
                session.commit()

    def delete_task(self, task_id: int):
        with self.get_session() as session:
            t = session.query(Task).filter_by(id=task_id).first()
            if t:
                session.delete(t)
                session.commit()

    # ── Bug Reports ──────────────────────────────────────────────────────────

    def create_bug_report(self, project_id: int, title: str, stack_trace: str,
                          analysis: str, suggested_fix: str, severity: str = "medium") -> int:
        with self.get_session() as session:
            b = BugReport(
                project_id=project_id, title=title, stack_trace=stack_trace,
                analysis=analysis, suggested_fix=suggested_fix, severity=severity
            )
            session.add(b)
            session.commit()
            session.refresh(b)
            return b.id

    def get_bug_reports(self, project_id: int) -> List[Dict]:
        with self.get_session() as session:
            bugs = session.query(BugReport).filter_by(project_id=project_id).order_by(BugReport.created_at.desc()).all()
            return [
                {
                    "id": b.id, "title": b.title, "stack_trace": b.stack_trace,
                    "analysis": b.analysis, "suggested_fix": b.suggested_fix,
                    "severity": b.severity, "status": b.status, "created_at": str(b.created_at)
                }
                for b in bugs
            ]

    def update_bug_status(self, bug_id: int, status: str):
        with self.get_session() as session:
            b = session.query(BugReport).filter_by(id=bug_id).first()
            if b:
                b.status = status
                session.commit()

    # ── Memory Logs ──────────────────────────────────────────────────────────

    def save_memory(self, memory_type: str, content: str, project_id: int = None, vector_id: str = None):
        with self.get_session() as session:
            m = MemoryLog(
                project_id=project_id, memory_type=memory_type,
                content=content, vector_id=vector_id
            )
            session.add(m)
            session.commit()

    def get_memories(self, project_id: int = None, memory_type: str = None) -> List[Dict]:
        with self.get_session() as session:
            q = session.query(MemoryLog)
            if project_id:
                q = q.filter_by(project_id=project_id)
            if memory_type:
                q = q.filter_by(memory_type=memory_type)
            mems = q.order_by(MemoryLog.created_at.desc()).limit(100).all()
            return [
                {"id": m.id, "type": m.memory_type, "content": m.content, "created_at": str(m.created_at)}
                for m in mems
            ]

    # ── Activity ──────────────────────────────────────────────────────────────

    def log_activity(self, action: str, detail: str = "", project_id: int = None, user_id: int = 1):
        with self.get_session() as session:
            a = ActivityLog(action=action, detail=detail, project_id=project_id, user_id=user_id)
            session.add(a)
            session.commit()

    def get_activity(self, project_id: int = None, limit: int = 50) -> List[Dict]:
        with self.get_session() as session:
            q = session.query(ActivityLog)
            if project_id:
                q = q.filter_by(project_id=project_id)
            acts = q.order_by(ActivityLog.created_at.desc()).limit(limit).all()
            return [{"action": a.action, "detail": a.detail, "time": str(a.created_at)} for a in acts]

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_project_stats(self, project_id: int) -> Dict:
        with self.get_session() as session:
            tasks = session.query(Task).filter_by(project_id=project_id).all()
            bugs = session.query(BugReport).filter_by(project_id=project_id).all()
            convos = session.query(Conversation).filter_by(project_id=project_id).count()
            return {
                "total_tasks": len(tasks),
                "todo": sum(1 for t in tasks if t.status == "todo"),
                "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                "done": sum(1 for t in tasks if t.status == "done"),
                "total_bugs": len(bugs),
                "open_bugs": sum(1 for b in bugs if b.status == "open"),
                "resolved_bugs": sum(1 for b in bugs if b.status == "resolved"),
                "total_conversations": convos,
            }
