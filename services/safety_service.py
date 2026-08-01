# hospital-information-assistant/services/safety_service.py

import re
from typing import Tuple, Dict, Any
from config.settings import MANDATORY_DISCLAIMER, EMERGENCY_RESPONSE, SAFE_REFUSAL_RESPONSE
from utils.logger import get_logger

logger = get_logger("SafetyService")


class SafetyService:
    """
    Enforces medical safety rules, emergency detection, intent screening,
    and disclaimer injection.
    """

    # Keywords that indicate a life-threatening or immediate emergency
    EMERGENCY_KEYWORDS = [
        "chest pain", "heart attack", "can't breathe", "cannot breathe", "shortness of breath",
        "stroke", "unconscious", "heavy bleeding", "severe trauma", "poisoning",
        "suicide", "dying", "fainted", "seizure", "anaphylaxis"
    ]

    # Regex patterns that indicate a user asking for personal medical diagnosis or prescriptions
    DIAGNOSIS_PATTERNS = [
        r"\bwhat disease do i have\b",
        r"\bdiagnose me\b",
        r"\bdo i have\b",
        r"\bwhat illness do i have\b",
        r"\bam i sick with\b",
        r"\bwhat condition is this\b"
    ]

    TREATMENT_PATTERNS = [
        r"\bwhat medicine should i take\b",
        r"\bwhat treatment should i follow\b",
        r"\bprescribe\b",
        r"\bhow to treat my\b",
        r"\bcure for my\b",
        r"\bwhich pill\b",
        r"\bdosage for\b"
    ]

    def evaluate_query_safety(self, query: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Screens user input prior to LLM execution.
        Returns:
            (is_safe_to_proceed: bool, override_response: str, metadata: dict)
        """
        clean_query = query.lower().strip()

        # 1. Emergency Check
        for kw in self.EMERGENCY_KEYWORDS:
            if kw in clean_query:
                logger.warning(f"Emergency keyword detected: '{kw}'")
                return False, f"{EMERGENCY_RESPONSE}\n\n{MANDATORY_DISCLAIMER}", {"type": "emergency"}

        # 2. Direct Diagnosis Request Check
        for pattern in self.DIAGNOSIS_PATTERNS:
            if re.search(pattern, clean_query):
                logger.info(f"Diagnosis request detected by pattern: '{pattern}'")
                return False, f"{SAFE_REFUSAL_RESPONSE}\n\n{MANDATORY_DISCLAIMER}", {"type": "refusal_diagnosis"}

        # 3. Direct Treatment / Prescription Request Check
        for pattern in self.TREATMENT_PATTERNS:
            if re.search(pattern, clean_query):
                logger.info(f"Treatment/Prescription request detected by pattern: '{pattern}'")
                return False, f"{SAFE_REFUSAL_RESPONSE}\n\n{MANDATORY_DISCLAIMER}", {"type": "refusal_treatment"}

        # Query passes pre-screening
        return True, "", {"type": "safe"}

    def append_disclaimer(self, text: str, force: bool = False) -> str:
        """
        Appends the standard medical disclaimer if not already present in the text.
        """
        if MANDATORY_DISCLAIMER in text:
            return text

        return f"{text}\n\n---\n*{MANDATORY_DISCLAIMER}*"


# Module-level singleton instance
safety_service = SafetyService()
