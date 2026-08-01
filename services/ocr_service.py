# hospital-information-assistant/services/ocr_service.py

import os
import io
from pathlib import Path
from typing import Dict, Any, Union
from PIL import Image

# PyMuPDF for PDF text extraction
try:
    import fitz  
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# EasyOCR / Pillow fallback for image text extraction
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

from services.safety_service import safety_service
from utils.logger import get_logger

logger = get_logger("OCRService")


class OCRService:
    """
    Extracts text from uploaded medical documents (PDFs and images)
    and provides non-diagnostic educational summaries of medical terms.
    """

    def __init__(self):
        self._ocr_reader = None

    def _get_easyocr_reader(self):
        """Lazy loader for EasyOCR reader model."""
        if self._ocr_reader is None and HAS_EASYOCR:
            logger.info("Initializing EasyOCR reader instance...")
            # Run on CPU for broad compatibility
            self._ocr_reader = easyocr.Reader(['en'], gpu=False)
        return self._ocr_reader

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extracts plain text from a PDF document using PyMuPDF."""
        if not HAS_PYMUPDF:
            logger.error("PyMuPDF (fitz) is not installed.")
            return "Error: PyMuPDF package is missing. Cannot extract PDF text."

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = []
            for page in doc:
                extracted_text.append(page.get_text())
            
            full_text = "\n".join(extracted_text).strip()
            return full_text if full_text else "No extractable text found in PDF."
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            return f"Error extracting text from PDF document: {str(e)}"

    def extract_text_from_image(self, file_bytes: bytes) -> str:
        """Extracts text from PNG/JPG image files using EasyOCR or basic PIL fallback."""
        if HAS_EASYOCR:
            try:
                reader = self._get_easyocr_reader()
                results = reader.readtext(file_bytes)
                extracted_lines = [item[1] for item in results]
                full_text = "\n".join(extracted_lines).strip()
                return full_text if full_text else "No extractable text detected in image."
            except Exception as e:
                logger.error(f"EasyOCR extraction error: {e}")

        # Fallback if EasyOCR is unavailable or encounters an error
        try:
            image = Image.open(io.BytesIO(file_bytes))
            return f"Image uploaded successfully ({image.width}x{image.height} px). OCR text extraction requires easyocr."
        except Exception as e:
            logger.error(f"Image opening error: {e}")
            return f"Failed to process image file: {str(e)}"

    def process_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Main entry point: Identifies file type, extracts text, and generates
        a safe educational summary with safety guardrails.
        """
        ext = Path(filename).suffix.lower()

        logger.info(f"Processing document: {filename} ({len(file_bytes)} bytes)")

        if ext == ".pdf":
            extracted_text = self.extract_text_from_pdf(file_bytes)
        elif ext in [".png", ".jpg", ".jpeg"]:
            extracted_text = self.extract_text_from_image(file_bytes)
        else:
            return {
                "success": False,
                "error": f"Unsupported file extension '{ext}'. Please upload a PDF, PNG, JPG, or JPEG file.",
                "extracted_text": "",
                "educational_summary": ""
            }

        # Build educational response
        educational_summary = self._generate_educational_summary(extracted_text)

        return {
            "success": True,
            "filename": filename,
            "extracted_text": extracted_text,
            "educational_summary": safety_service.append_disclaimer(educational_summary)
        }

    def _generate_educational_summary(self, text: str) -> str:
        """
        Generates general educational definitions for common lab report terms
        found in the text without giving medical advice.
        """
        text_lower = text.lower()
        terms_explained = []

        dictionary = {
            "hemoglobin": "Hemoglobin is a protein in red blood cells that carries oxygen throughout the body.",
            "glucose": "Glucose measures the level of sugar in the blood, commonly checked for diabetes screening.",
            "wbc": "White Blood Cells (WBC) are part of the immune system and help defend against infections.",
            "platelet": "Platelets are blood cell fragments that help the blood clot to stop bleeding.",
            "cholesterol": "Cholesterol is a lipid substance used by cells; levels are checked to monitor heart health.",
            "creatinine": "Creatinine is a waste product filtered by the kidneys, used to assess kidney function."
        }

        for term, explanation in dictionary.items():
            if term in text_lower:
                terms_explained.append(f"• **{term.capitalize()}**: {explanation}")

        if terms_explained:
            summary = (
                "### Educational Medical Terminology Breakdown\n"
                "The following standard medical parameters were recognized in your document:\n\n" +
                "\n".join(terms_explained) +
                "\n\n*Note: This breakdown is purely for general educational reference. "
                "Only your physician can evaluate your specific clinical results.*"
            )
        else:
            summary = (
                "### Document Text Successfully Extracted\n"
                "The document text was extracted above. No standard general lab parameters "
                "were recognized in our educational quick-reference dictionary."
            )

        return summary


# Module-level singleton instance
ocr_service = OCRService()