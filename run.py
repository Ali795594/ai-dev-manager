#!/usr/bin/env python3
"""
AI Dev Manager - Unified launcher
Usage:
  python run.py            # Start both API + UI
  python run.py --api      # API only (port 8000)
  python run.py --ui       # UI only (port 8501)
  python run.py --setup    # First-time setup check
"""
import sys
import os
import subprocess
import threading
import time
import shutil
from pathlib import Path

# ── Resolve project root (the folder that contains THIS file) ─────────────────
ROOT = Path(__file__).resolve().parent

# Sanity-check: make sure we're pointing at the right folder
if not (ROOT / "app" / "main.py").exists():
    print(f"ERROR: Cannot find app/main.py under {ROOT}")
    print("Make sure you run:  python run.py  from inside the project folder,")
    print("or that run.py sits at the top level of the project (next to the app/ folder).")
    sys.exit(1)

os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        example = ROOT / ".env.example"
        if example.exists():
            shutil.copy(example, env_file)
            print("📄 Created .env from .env.example — add your ANTHROPIC_API_KEY")
        else:
            env_file.write_text("ANTHROPIC_API_KEY=your_key_here\n")
            print("📄 Created .env — add your ANTHROPIC_API_KEY")

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_file, override=True)
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("your_"):
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set in .env")
        print("   Get your key at: https://console.anthropic.com")
        return False
    print("✅ ANTHROPIC_API_KEY found")
    return True


def ensure_dirs():
    dirs = [
        "app/database",
        "app/memory/chroma_db",
        "app/agents",
        "app/repository",
        "app/orchestration",
        "app/ui",
        "uploads",
        "logs",
    ]
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    for pkg in ["app", "app/agents", "app/database", "app/memory",
                "app/repository", "app/ui", "app/orchestration"]:
        init = ROOT / pkg / "__init__.py"
        if not init.exists():
            init.write_text("")

    print("✅ Directories ready")
    print(f"   Project root: {ROOT}")


def start_api():
    print("🚀 Starting API server on http://localhost:8000")
    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "warning",
        ],
        cwd=str(ROOT),
    )


def start_ui():
    print("🎨 Starting UI on http://localhost:8501")
    time.sleep(3)

    # Build absolute path using pathlib — correct separators on every OS
    ui_script = ROOT / "app" / "ui" / "streamlit_app.py"

    if not ui_script.exists():
        print(f"ERROR: Streamlit app not found at {ui_script}")
        return

    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(ui_script),
            "--server.port", "8501",
            "--server.headless", "true",
            "--theme.base", "dark",
            "--theme.primaryColor", "#7c6af7",
            "--theme.backgroundColor", "#0d0d0f",
            "--theme.secondaryBackgroundColor", "#141416",
            "--theme.textColor", "#e8e8f0",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(ROOT),
    )


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--both"

    print("⚡ AI Dev Manager")
    print("─" * 40)

    ensure_dirs()

    if mode == "--setup":
        check_env()
        print("\n✅ Setup complete! Run: python run.py")
        return

    check_env()

    if mode == "--api":
        start_api()
    elif mode == "--ui":
        start_ui()
    else:
        print("Starting API + UI…\n")
        print("  API:  http://localhost:8000")
        print("  UI:   http://localhost:8501")
        print("  Docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop\n")

        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        start_ui()


if __name__ == "__main__":
    main()