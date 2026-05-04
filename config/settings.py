import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# API Keys
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Local Setup
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", BASE_DIR / "ObsidianVault"))

# Directories
RESEARCH_DIR = OBSIDIAN_VAULT_PATH / "01_Research"
LESSONS_LEARNED_DIR = OBSIDIAN_VAULT_PATH / "02_Lessons_Learned"
SYSTEM_LOGS_DIR = OBSIDIAN_VAULT_PATH / "03_System_Logs"
TEMPLATES_DIR = OBSIDIAN_VAULT_PATH / "04_Templates"
