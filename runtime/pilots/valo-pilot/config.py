import os
from dotenv import load_dotenv

load_dotenv()

# LLM endpoint — replace with customer's API
LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:11434/api/generate")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# VAIG config
AUDIT_LOG_PATH  = os.getenv("AUDIT_LOG_PATH", "vaig_audit.jsonl")
L4_AUTO_TRIGGER = False  # Security: never enable without explicit review
