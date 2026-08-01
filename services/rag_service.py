# hospital-information-assistant/services/rag_service.py

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config.settings import DATA_DIR, KNOWLEDGE_BASE_DIR
from utils.logger import get_logger

logger = get_logger("RAGService")


class RAGService:
    """
    Handles knowledge base indexing, FAISS vector store creation,
    and similarity retrieval for hospital information.
    """

    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or (DATA_DIR / "hospital_data.json")
        self.index_path = KNOWLEDGE_BASE_DIR / "faiss_index"
        self._data = None  # Store loaded raw data for direct access by app
        
        # Initialize lightweight open-source embedding model
        logger.info("Initializing HuggingFace embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        self.vector_store: Optional[FAISS] = None

    def _load_hospital_data(self) -> Dict[str, Any]:
        """Loads structured JSON hospital data."""
        if not self.data_file.exists():
            logger.error(f"Hospital data file not found at {self.data_file}")
            raise FileNotFoundError(f"Missing hospital data file: {self.data_file}")

        with open(self.data_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            self._data = raw_data  # Cache for direct access
            return raw_data

    def get_hospital_data(self) -> Dict[str, Any]:
        """Returns the loaded hospital data, loading it if necessary."""
        if self._data is None:
            return self._load_hospital_data()
        return self._data

    def _transform_json_to_documents(self, raw_data: Dict[str, Any]) -> List[Document]:
        """
        Flattens complex JSON structures into semantic text chunks optimized for RAG.
        """
        documents: List[Document] = []

        # 1. Hospital General Overview & Contact Info
        hospital = raw_data.get("hospital_info", {})
        general_text = (
            f"Hospital Name: {hospital.get('name')}\n"
            f"Tagline: {hospital.get('tagline')}\n"
            f"Overview: {hospital.get('overview')}\n"
            f"Address: {hospital.get('address')}\n"
            f"Phone: {hospital.get('phone')}\n"
            f"Emergency Helpline: {hospital.get('emergency_helpline')}\n"
            f"Email: {hospital.get('email')}\n"
            f"Location Landmarks: {hospital.get('location_landmarks')}"
        )
        documents.append(
            Document(page_content=general_text, metadata={"category": "general_overview"})
        )

        # 2. Visiting Hours
        visiting = raw_data.get("visiting_hours", {})
        visiting_rules = "\n".join([f"- {rule}" for rule in visiting.get("visiting_rules", [])])
        visiting_text = (
            f"General Wards Visiting Hours: {visiting.get('general_wards')}\n"
            f"ICU & Critical Care Visiting Hours: {visiting.get('icu_and_critical_care')}\n"
            f"Visiting Rules:\n{visiting_rules}"
        )
        documents.append(
            Document(page_content=visiting_text, metadata={"category": "visiting_hours"})
        )

        # 3. Emergency Services
        emergency = raw_data.get("emergency_services", {})
        emergency_text = (
            f"Emergency Services Availability: {emergency.get('availability')}\n"
            f"Emergency Department Location: {emergency.get('location')}\n"
            f"Emergency Facilities: {emergency.get('facilities')}\n"
            f"Emergency Guidance: {emergency.get('guidance')}"
        )
        documents.append(
            Document(page_content=emergency_text, metadata={"category": "emergency_services"})
        )

        # 4. Departments & Doctors
        for dept in raw_data.get("departments", []):
            doctors_str = ", ".join(
                [f"{doc['name']} ({doc['specialty']}, {doc['experience']} exp)" for doc in dept.get("doctors", [])]
            )
            services_str = ", ".join(dept.get("services", []))

            dept_text = (
                f"Department Name: {dept.get('name')}\n"
                f"Head of Department: {dept.get('head_of_department')}\n"
                f"Description: {dept.get('description')}\n"
                f"OP Timings (Outpatient Hours): {dept.get('op_timings')}\n"
                f"Location in Hospital: {dept.get('location')}\n"
                f"Doctors: {doctors_str}\n"
                f"Services Offered: {services_str}"
            )
            documents.append(
                Document(page_content=dept_text, metadata={"category": "department", "dept_id": dept.get("id")})
            )

        # 5. Facilities
        for facility in raw_data.get("facilities", []):
            facility_text = (
                f"Facility: {facility.get('name')}\n"
                f"Location: {facility.get('location')}\n"
                f"Description: {facility.get('description')}"
            )
            documents.append(
                Document(page_content=facility_text, metadata={"category": "facility"})
            )

        # 6. Admission Guidelines
        admission = raw_data.get("admission_guidelines", {})
        documents_required = ", ".join(admission.get("documents_required", []))
        admission_text = (
            f"Planned Admission Process: {admission.get('planned_admission')}\n"
            f"Emergency Admission Process: {admission.get('emergency_admission')}\n"
            f"Required Documents for Admission: {documents_required}"
        )
        documents.append(
            Document(page_content=admission_text, metadata={"category": "admission"})
        )

        # 7. Insurance and Billing
        billing = raw_data.get("insurance_and_billing", {})
        billing_text = (
            f"Cashless Insurance Coverage: {billing.get('cashless_insurance')}\n"
            f"Accepted Payment Modes: {billing.get('payment_modes')}\n"
            f"Billing Desk Timings: {billing.get('billing_desk_timings')}"
        )
        documents.append(
            Document(page_content=billing_text, metadata={"category": "billing"})
        )

        logger.info(f"Transformed JSON into {len(documents)} document chunks for RAG.")
        return documents

    def build_or_load_vector_store(self, force_rebuild: bool = False) -> FAISS:
        """
        Builds a new FAISS vector store or loads an existing index from disk.
        """
        if not force_rebuild and self.index_path.exists():
            logger.info("Loading existing FAISS vector store from disk...")
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=str(self.index_path),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
                return self.vector_store
            except Exception as e:
                logger.warning(f"Failed to load vector index ({e}). Rebuilding index...")

        logger.info("Building new FAISS vector index from hospital JSON data...")
        raw_data = self._load_hospital_data()
        docs = self._transform_json_to_documents(raw_data)

        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        self.vector_store.save_local(folder_path=str(self.index_path))
        logger.info(f"FAISS index successfully saved at '{self.index_path}'.")
        return self.vector_store

    def retrieve_relevant_context(self, query: str, top_k: int = 3) -> str:
        """
        Retrieves top_k most relevant documents for a given query and formats them as string context.
        """
        if self.vector_store is None:
            self.build_or_load_vector_store()

        logger.info(f"Searching vector index for query: '{query}'")
        results = self.vector_store.similarity_search(query, k=top_k)

        if not results:
            return ""

        context_blocks = []
        for idx, doc in enumerate(results, 1):
            context_blocks.append(f"--- Document Chunk {idx} ---\n{doc.page_content}")

        return "\n\n".join(context_blocks)


# Module-level singleton instance for convenience
rag_service = RAGService()
