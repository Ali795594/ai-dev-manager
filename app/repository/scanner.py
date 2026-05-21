"""
Repository Scanner - scans local directories and extracts project intelligence
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import chardet

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt",
    ".html", ".css", ".scss", ".sass", ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env.example",
    ".md", ".txt", ".sh", ".bash", ".dockerfile", ".sql",
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".next", "dist", "build", ".dist", "coverage", ".nyc_output",
    "target", ".cargo", ".gradle", ".idea", ".vscode",
    "chroma_db", "uploads", "logs", ".pytest_cache",
}

TECH_PATTERNS = {
    "FastAPI": [r"fastapi", r"from fastapi"],
    "Flask": [r"from flask", r"import flask"],
    "Django": [r"django", r"INSTALLED_APPS"],
    "Express.js": [r"express\(\)", r"require\(['\"]express"],
    "React": [r"import React", r"from ['\"]react['\"]"],
    "Vue.js": [r"createApp\|new Vue"],
    "Next.js": [r"next/", r"getServerSideProps"],
    "SQLite": [r"sqlite", r"\.db"],
    "PostgreSQL": [r"postgresql", r"psycopg2", r"pg\.Pool"],
    "MongoDB": [r"pymongo", r"mongoose", r"MongoClient"],
    "Redis": [r"redis", r"RedisClient"],
    "Docker": [r"FROM ", r"EXPOSE ", r"RUN apt"],
    "JWT": [r"jwt", r"jsonwebtoken", r"Bearer"],
    "OAuth": [r"oauth", r"OAuth2"],
    "Anthropic": [r"anthropic", r"claude"],
    "OpenAI": [r"openai", r"ChatGPT"],
    "LangChain": [r"langchain"],
    "SQLAlchemy": [r"sqlalchemy", r"Column\("],
    "Prisma": [r"prisma", r"@prisma"],
    "TypeScript": [r"\.ts$", r"interface ", r": string\b"],
    "Python": [r"\.py$", r"def ", r"import "],
    "JavaScript": [r"\.js$", r"const ", r"require\("],
    "Kubernetes": [r"apiVersion:", r"kubectl"],
    "GraphQL": [r"graphql", r"type Query"],
}


class RepositoryScanner:
    def __init__(self):
        self.max_file_size = 500 * 1024  # 500KB

    def is_safe_path(self, path: str) -> bool:
        """Validate that the path is safe to scan (no traversal)."""
        try:
            resolved = Path(path).resolve()
            # Ensure it's an absolute path that exists
            return resolved.exists() and resolved.is_dir()
        except Exception:
            return False

    def read_file_safe(self, path: Path) -> Optional[str]:
        """Safely read a file, handling encoding issues."""
        try:
            if path.stat().st_size > self.max_file_size:
                return None
            raw = path.read_bytes()
            # Detect encoding
            detected = chardet.detect(raw)
            encoding = detected.get("encoding") or "utf-8"
            return raw.decode(encoding, errors="replace")
        except Exception:
            return None

    def scan_directory(self, root_path: str) -> Dict:
        """
        Scan a directory and extract project intelligence.
        Returns a structured report.
        """
        if not self.is_safe_path(root_path):
            return {"error": "Invalid or inaccessible path", "path": root_path}

        root = Path(root_path).resolve()
        files_data = []
        tech_hits = {}
        total_lines = 0
        file_count = 0
        dir_structure = []

        for file_path in root.rglob("*"):
            # Skip ignored directories
            if any(ig in file_path.parts for ig in IGNORE_DIRS):
                continue
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SCANNABLE_EXTENSIONS:
                continue

            rel_path = str(file_path.relative_to(root))
            content = self.read_file_safe(file_path)
            file_count += 1

            if content:
                lines = content.count("\n")
                total_lines += lines
                # Detect technologies
                for tech, patterns in TECH_PATTERNS.items():
                    for pat in patterns:
                        if re.search(pat, content, re.IGNORECASE):
                            tech_hits[tech] = tech_hits.get(tech, 0) + 1
                            break
                files_data.append({
                    "path": rel_path,
                    "extension": file_path.suffix,
                    "lines": lines,
                    "size": file_path.stat().st_size,
                    "content_preview": content[:500],
                    "content": content,
                })
            else:
                files_data.append({
                    "path": rel_path,
                    "extension": file_path.suffix,
                    "lines": 0,
                    "size": file_path.stat().st_size,
                    "content_preview": "[binary or too large]",
                    "content": "",
                })

        # Collect directory structure (top-level only)
        try:
            for item in sorted(root.iterdir()):
                if item.name not in IGNORE_DIRS and not item.name.startswith("."):
                    dir_structure.append(f"{'📁' if item.is_dir() else '📄'} {item.name}")
        except Exception:
            pass

        # Detect primary language
        ext_counts = {}
        for f in files_data:
            ext = f["extension"]
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        primary_ext = max(ext_counts, key=ext_counts.get) if ext_counts else ""

        tech_stack = sorted(tech_hits.keys(), key=lambda t: -tech_hits[t])

        # Find key files
        key_files = self._find_key_files(files_data)

        return {
            "root": str(root),
            "name": root.name,
            "file_count": file_count,
            "total_lines": total_lines,
            "tech_stack": tech_stack,
            "primary_language": self._ext_to_lang(primary_ext),
            "directory_structure": dir_structure,
            "key_files": key_files,
            "files": files_data,
            "ext_breakdown": ext_counts,
        }

    def _ext_to_lang(self, ext: str) -> str:
        mapping = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".jsx": "React/JSX", ".tsx": "TypeScript/React", ".rb": "Ruby",
            ".go": "Go", ".rs": "Rust", ".java": "Java", ".cs": "C#",
            ".cpp": "C++", ".c": "C", ".swift": "Swift", ".kt": "Kotlin",
            ".php": "PHP",
        }
        return mapping.get(ext, ext or "Unknown")

    def _find_key_files(self, files: List[Dict]) -> List[str]:
        """Identify key configuration and entry point files."""
        key_names = {
            "package.json", "requirements.txt", "pyproject.toml", "setup.py",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "README.md", "README.rst", ".env.example", "main.py", "app.py",
            "index.js", "index.ts", "server.js", "manage.py",
            "Makefile", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        }
        found = []
        for f in files:
            name = Path(f["path"]).name
            if name in key_names:
                found.append(f["path"])
        return found[:10]

    def build_context_summary(self, scan_result: Dict) -> str:
        """Build a concise context string for the AI to understand the project."""
        if "error" in scan_result:
            return f"Error scanning repository: {scan_result['error']}"

        lines = [
            f"Project: {scan_result['name']}",
            f"Location: {scan_result['root']}",
            f"Files: {scan_result['file_count']} | Lines of code: {scan_result['total_lines']:,}",
            f"Primary language: {scan_result['primary_language']}",
            f"Tech stack: {', '.join(scan_result['tech_stack'][:10]) or 'Unknown'}",
            "",
            "Directory structure:",
            *scan_result["directory_structure"][:15],
            "",
            "Key files:",
            *[f"  - {f}" for f in scan_result["key_files"]],
        ]
        return "\n".join(lines)

    def get_file_content(self, root_path: str, rel_path: str) -> Optional[str]:
        """Safely get the content of a specific file."""
        try:
            root = Path(root_path).resolve()
            target = (root / rel_path).resolve()
            # Prevent path traversal
            target.relative_to(root)
            if target.is_file():
                return self.read_file_safe(target)
        except Exception:
            pass
        return None
