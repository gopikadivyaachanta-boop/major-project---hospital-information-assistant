# hospital-information-assistant/config/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Core App Configurations
APP_TITLE = "Hospital Information Assistant"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# File Paths
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"

# Ensure runtime directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

# File Validation Constraints
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
MAX_FILE_SIZE_MB = 10

# Medical Safety Disclaimers & Rules
MANDATORY_DISCLAIMER = (
    "Disclaimer: This Hospital Information Assistant provides general informational "
    "and educational content only. It is not a medical diagnosis tool and does not provide "
    "medical treatment recommendations. Always consult a qualified healthcare professional "
    "for medical advice, diagnosis, or treatment."
)

EMERGENCY_RESPONSE = (
    "If you are experiencing a medical emergency, contact your local emergency services "
    "or visit the nearest emergency department immediately."
)

SAFE_REFUSAL_RESPONSE = (
    "I can provide general educational information only. I cannot diagnose medical "
    "conditions or recommend medicines or treatment. Please consult a qualified healthcare professional."
)
