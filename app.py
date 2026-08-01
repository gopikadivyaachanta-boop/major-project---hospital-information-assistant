# hospital-information-assistant/app.py

import streamlit as st
import json
from pathlib import Path

# Import custom services
from config.settings import APP_TITLE, MANDATORY_DISCLAIMER, DATA_DIR
from services.gemini_service import gemini_service
from services.appointment_service import appointment_service
from services.ocr_service import ocr_service
from services.rag_service import rag_service
from utils.logger import get_logger

logger = get_logger("App")

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .emergency-box {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
    .disclaimer-footer {
        font-size: 0.82rem;
        color: #6B7280;
        border-top: 1px solid #E5E7EB;
        padding-top: 10px;
        margin-top: 30px;
    }
    .card {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Session State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I am the official AI Assistant for **MetroCare General Hospital**.\n\n"
                "I can help you with:\n"
                "- Finding department OPD timings & available specialists\n"
                "- Understanding appointment booking & preparation steps\n"
                "- Extracting educational definitions from uploaded medical documents\n\n"
                "*How can I assist you today?*"
            )
        }
    ]

# -----------------------------------------------------------------------------
# 3. Sidebar Setup
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital-2.png", width=70)
    st.markdown("### MetroCare Hospital")
    st.caption("Patient Information & Support Portal")
    
    st.markdown("---")
    
    # Emergency Information Block
    st.markdown("""
    <div class="emergency-box">
        <strong style="color: #991B1B;">🚨 Medical Emergency?</strong><br>
        Do not use this chat. Please call immediately:<br>
        <strong style="font-size: 1.1rem; color: #DC2626;">+1 (800) 555-9111</strong><br>
        or visit <strong>Gate 2 Emergency Wing</strong>.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### 📞 Key Contacts")
    st.markdown("- **General Helpline**: +1 (800) 555-0199")
    st.markdown("- **OPD Reception**: Block A, Ground Floor")
    st.markdown("- **OPD Hours**: Mon–Sat, 8:00 AM – 4:00 PM")
    
    st.markdown("---")
    
    if st.button("🧹 Clear Conversation History", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

    st.markdown("---")
    st.caption("Powered by Google Gemini & RAG Architecture")

# -----------------------------------------------------------------------------
# 4. Header Section
# -----------------------------------------------------------------------------
st.markdown(f'<div class="main-header">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Your 24/7 intelligent guide for hospital information, departments, and appointment preparation.</div>',
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 5. Tabbed Interface Architecture
# -----------------------------------------------------------------------------
tab_chat, tab_depts, tab_appointments, tab_ocr = st.tabs([
    "💬 AI Chat Assistant",
    "🏥 Department Directory",
    "📅 Appointment Guidance",
    "📄 Medical Document Reader"
])

# =============================================================================
# TAB 1: AI Chat Assistant
# =============================================================================
with tab_chat:
    st.markdown("##### Ask any question about MetroCare services, doctors, or visit procedures:")
    
    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input Box
    if user_prompt := st.chat_input("e.g., What are Cardiology OP timings? Or who is the specialist for Neurology?"):
        # 1. Display User Message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # 2. Generate Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Searching hospital knowledge base..."):
                response_text = gemini_service.generate_response(
                    user_query=user_prompt,
                    chat_history=st.session_state.messages[:-1]
                )
                st.markdown(response_text)
                
        st.session_state.messages.append({"role": "assistant", "content": response_text})

# =============================================================================
# TAB 2: Department Directory
# =============================================================================
with tab_depts:
    st.markdown("### 🏥 Hospital Department & Specialist Directory")
    
    hospital_data = rag_service.get_hospital_data().get("departments", [])
    
    if hospital_data:
        search_kw = st.text_input("🔍 Search by department name, medical specialty, or doctor:", "").strip().lower()
        
        filtered_depts = [
            d for d in hospital_data
            if search_kw in d["name"].lower()
            or search_kw in d["id"].lower()
            or any(search_kw in doc["name"].lower() or search_kw in doc["specialty"].lower() for doc in d.get("doctors", []))
        ]
        
        if not filtered_depts:
            st.warning(f"No departments or specialists found matching '{search_kw}'.")
        else:
            for dept in filtered_depts:
                with st.expander(f"📌 **{dept['name']}** — {dept['location']}", expanded=True):
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown(f"**🕒 OP Timings:** {dept['op_timings']}")
                        st.markdown(f"**📍 Location:** {dept['location']}")
                        st.markdown("**🛠️ Key Services:**")
                        for srv in dept.get("services", []):
                            st.markdown(f"- {srv}")
                            
                    with col2:
                        st.markdown("**👨‍⚕️ Available Doctors & Specialists:**")
                        for doc in dept.get("doctors", []):
                            st.markdown(
                                f"- **{doc['name']}**  \n"
                                f"  *Specialty:* {doc.get('specialty', 'N/A')} | *Experience:* {doc.get('experience', 'N/A')}"
                            )
    else:
        st.error("Hospital knowledge base data is currently unavailable.")

# =============================================================================
# TAB 3: Appointment Guidance
# =============================================================================
with tab_appointments:
    st.markdown("### 📅 Outpatient Appointment Guidance & Checklist")
    
    workflow = appointment_service.get_general_appointment_workflow()
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### 📱 Booking Options")

        # Functional Online Portal navigation — opens the dedicated booking webpage
        st.markdown("")
        if st.button("🌐 **Book Online Now — Open Booking Portal**", type="primary", use_container_width=True):
            st.switch_page("pages/1_Online_Booking_Portal.py")
        st.caption("Click above to book instantly via our online portal.")

        for opt in workflow["booking_options"]:
            st.markdown(f"• **{opt['mode']}**: {opt['details']}")
            
        st.markdown("\n#### 📋 Required Details for Registration")
        for req in workflow["required_information"]:
            st.markdown(f"- {req}")
            
    with col_b:
        st.markdown("#### ✅ Patient Visit Checklist")
        for item in workflow["preparation_checklist"]:
            st.checkbox(item, key=f"chk_{hash(item)}")
            
        st.markdown("\n#### 🔄 Rescheduling & Cancellation Policy")
        st.info(workflow["cancellation_and_rescheduling"])

# =============================================================================
# TAB 4: Medical Document Reader
# =============================================================================
with tab_ocr:
    st.markdown("### 📄 Educational Lab Report & Document Reader")
    st.info(
        "Upload a scanned report or image (PDF, PNG, JPG) to extract document text and view "
        "general educational definitions for standard medical parameters."
    )
    
    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supported formats: PDF, PNG, JPG, JPEG (Max 10MB)"
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        
        with st.spinner("Extracting text and identifying terms..."):
            result = ocr_service.process_document(
                file_bytes=file_bytes,
                filename=uploaded_file.name
            )
            
        if result["success"]:
            st.success(f"Successfully processed `{result['filename']}`!")
            
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                st.markdown("#### 📜 Extracted Raw Text")
                st.text_area(
                    label="Extracted Text Output",
                    value=result["extracted_text"],
                    height=300
                )
                
            with res_col2:
                st.markdown("#### 📚 Educational Breakdown")
                st.markdown(result["educational_summary"])
        else:
            st.error(result.get("error", "Failed to read document."))

# -----------------------------------------------------------------------------
# 6. Global Disclaimer Footer
# -----------------------------------------------------------------------------
st.markdown(
    f'<div class="disclaimer-footer"><strong>Legal Disclaimer:</strong> {MANDATORY_DISCLAIMER}</div>',
    unsafe_allow_html=True
)
