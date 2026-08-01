# hospital-information-assistant/utils/validators.py

import os
from pathlib import Path
from config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

def validate_uploaded_file(file_path: Path) -> tuple[bool, str]:
    """
    Validates uploaded document extension and file size.
    Returns (is_valid: bool, error_message: str)
    """
    if not file_path.exists():
        return False, "Uploaded file does not exist."

    ext = file_path.suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file format '.{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}."

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File size exceeds maximum limit of {MAX_FILE_SIZE_MB}MB."

    return True, "File is valid."

def sanitize_user_input(text: str) -> str:
    """Sanitizes plain text input from user queries."""
    if not text:
        return ""
    # Strip whitespace and cap length to prevent prompt injection overload
    return text.strip()[:1000]
