# hospital-information-assistant/services/gemini_service.py

import os
from typing import List, Dict, Optional
import google.generativeai as genai

from config.settings import GEMINI_API_KEY, MANDATORY_DISCLAIMER, SAFE_REFUSAL_RESPONSE
from services.rag_service import rag_service
from services.safety_service import safety_service
from utils.logger import get_logger

logger = get_logger("GeminiService")


SYSTEM_PROMPT = """You are the official AI Assistant for MetroCare General Hospital. Your sole purpose is to provide polite, accurate, professional, and clear hospital information and general educational guidance.

STRICT OPERATIONAL RULES:
1. **Hospital Information Grounding**:
   - Answer hospital-related questions (departments, doctors, timings, services, facilities, contact info) strictly using the provided "HOSPITAL KNOWLEDGE BASE CONTEXT".
   - If the requested hospital information is NOT present in the provided context, state clearly: "I don't have enough information about that in the hospital knowledge base." Do NOT invent or hallucinate hospital details.

2. **Medical Safety Guardrails**:
   - You are NOT a medical doctor. NEVER diagnose diseases, predict medical conditions, prescribe medicines, or recommend personalized treatment plans.
   - If the user asks for diagnosis or treatment, reply politely: "I can provide general educational information only. I cannot diagnose medical conditions or recommend medicines or treatment. Please consult a qualified healthcare professional."
   - For educational medical topics, keep explanations simple, clear, and objective.

3. **Emergency Protocol**:
   - If a user mentions severe emergency symptoms (chest pain, severe bleeding, difficulty breathing, stroke), immediately instruct them to contact local emergency services or visit the nearest emergency department.

4. **Tone & Style**:
   - Be empathetic, polite, concise, and professional.
   - Use simple language suitable for patients and visitors.
"""


class GeminiService:
    """
    Handles Gemini LLM calls, RAG context injection, conversation formatting,
    and response generation.
    """

    def __init__(self):
        self.api_key = GEMINI_API_KEY
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            genai.configure(api_key=self.api_key)
            # Use gemini-1.5-flash or gemini-2.5-flash for fast and reliable responses
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.is_configured = True
            logger.info("Gemini API successfully configured.")
        else:
            self.model = None
            self.is_configured = False
            logger.warning("Gemini API key is missing or default. LLM fallback responses will be used.")

    def generate_response(self, user_query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generates a grounded answer using Safety Check -> RAG Context -> Gemini LLM.
        """
        # Step 1: Pre-screen query safety
        is_safe, override_response, meta = safety_service.evaluate_query_safety(user_query)
        if not is_safe:
            return override_response

        # Step 2: Retrieve RAG Context
        rag_context = rag_service.retrieve_relevant_context(user_query, top_k=3)
        
        # Fallback if API key is not configured
        if not self.is_configured:
            if rag_context:
                fallback_msg = (
                    f"**[Information from Hospital Knowledge Base]**:\n\n{rag_context}\n\n"
                    f"*(Note: Gemini API key is not configured in .env. Showing direct knowledge retrieval.)*"
                )
            else:
                fallback_msg = "I don't have enough information about that in the hospital knowledge base."
            return safety_service.append_disclaimer(fallback_msg)

        # Step 3: Construct Prompt with Context and History
        context_block = f"HOSPITAL KNOWLEDGE BASE CONTEXT:\n{rag_context}" if rag_context else "HOSPITAL KNOWLEDGE BASE CONTEXT: No relevant hospital documents found."

        history_str = ""
        if chat_history:
            formatted_history = []
            for msg in chat_history[-4:]: # Keep last 2 turns for context
                role = "User" if msg.get("role") == "user" else "Assistant"
                formatted_history.append(f"{role}: {msg.get('content')}")
            history_str = "\nRECENT CONVERSATION HISTORY:\n" + "\n".join(formatted_history)

        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{context_block}\n"
            f"{history_str}\n\n"
            f"USER QUERY: {user_query}\n\n"
            f"ASSISTANT RESPONSE:"
        )

        # Step 4: Call Gemini API safely
        try:
            logger.info(f"Sending prompt to Gemini API for query: '{user_query}'")
            response = self.model.generate_content(full_prompt)
            answer = response.text.strip()
            
            # Ensure safety disclaimer is attached if medical topics were discussed
            return safety_service.append_disclaimer(answer)

        except Exception as e:
            logger.error(f"Error invoking Gemini API: {e}")
            if rag_context:
                return safety_service.append_disclaimer(
                    f"Here is the relevant hospital information I found:\n\n{rag_context}"
                )
            return "I am currently unable to process your request. Please contact hospital reception directly at +1 (800) 555-0199."


# Module-level singleton instance
gemini_service = GeminiService()
