# hospital-information-assistant/pages/1_Online_Booking_Portal.py

"""
Online OPD Appointment Booking Portal
=====================================
A dedicated Streamlit page where patients can:
  1. Enter their personal / registration details.
  2. Choose a department, doctor, preferred date, and an available time slot.
  3. Confirm the booking and receive a unique appointment reference number.
  4. Look up or cancel an existing booking by its reference number.
"""

import datetime as dt

import streamlit as st

from config.settings import APP_TITLE, MANDATORY_DISCLAIMER
from services.booking_service import booking_service
from utils.logger import get_logger

logger = get_logger("BookingPortal")

# -----------------------------------------------------------------------------
# Page configuration & shared styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Online Booking Portal | MetroCare Hospital",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .portal-header {
            font-size: 2.1rem;
            color: #1E3A8A;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .portal-sub {
            font-size: 1.0rem;
            color: #4B5563;
            margin-bottom: 1.2rem;
        }
        .portal-card {
            background-color: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 14px;
        }
        .portal-success {
            background-color: #ECFDF5;
            border-left: 5px solid #10B981;
            padding: 14px 18px;
            border-radius: 6px;
            margin-bottom: 14px;
        }
        .disclaimer-footer {
            font-size: 0.82rem;
            color: #6B7280;
            border-top: 1px solid #E5E7EB;
            padding-top: 10px;
            margin-top: 30px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital-2.png", width=70)
    st.markdown("### MetroCare Hospital")
    st.caption("Outpatient Online Booking Portal")

    st.markdown("---")
    st.markdown("#### 📞 OPD Reception")
    st.markdown("- **Phone**: +1 (800) 555-0199")
    st.markdown("- **Working Hours**: Mon–Sat, 8:00 AM – 4:00 PM")
    st.markdown("- **Registration Desk**: Block A, Ground Floor")

    st.markdown("---")
    if st.button("🏠 Back to Main Assistant", use_container_width=True):
        st.switch_page("app.py")

    st.markdown("---")
    st.caption("Powered by MetroCare Digital Services")

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown('<div class="portal-header">🌐 Online Appointment Booking Portal</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="portal-sub">Book your outpatient consultation in under 2 minutes. '
    "A unique reference number will be issued for each confirmed appointment.</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "last_booking" not in st.session_state:
    st.session_state.last_booking = None

# -----------------------------------------------------------------------------
# Mode selector
# -----------------------------------------------------------------------------
mode_tabs = st.tabs(["➕ New Booking", "🔍 Find My Booking", "✖️ Cancel Booking"])

# =============================================================================
# TAB 1: NEW BOOKING
# =============================================================================
with mode_tabs[0]:
    st.markdown("### ➕ Request a New Appointment")

    try:
        departments = booking_service.get_departments()
    except FileNotFoundError as e:
        st.error(f"Hospital knowledge base unavailable: {e}")
        departments = []

    if not departments:
        st.warning("No departments are currently available for online booking. Please call the OPD reception at +1 (800) 555-0199.")
    else:
        # ---------------------------------------------------------------
        # Step 1: Patient details
        # ---------------------------------------------------------------
        st.markdown("#### 1️⃣ Patient Details")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name (as per Government ID) *", max_chars=100,
                                          placeholder="e.g., John A. Doe")
                dob = st.date_input(
                    "Date of Birth *",
                    value=None,
                    min_value=dt.date(1900, 1, 1),
                    max_value=dt.date.today(),
                    format="DD/MM/YYYY",
                )
                phone = st.text_input("Mobile / Contact Number *", max_chars=15,
                                      placeholder="e.g., +1 555 123 4567")
                id_type = st.selectbox(
                    "Government Photo ID Type *",
                    ["Passport", "Driver's License", "National ID", "Voter ID"],
                )
                id_number = st.text_input("Government Photo ID Number *", max_chars=40,
                                          placeholder="Enter your ID number")

            with col2:
                gender = st.selectbox("Gender *", ["Male", "Female", "Other", "Prefer not to say"])
                age = st.number_input("Age (if DOB unavailable)", min_value=0, max_value=120, value=0,
                                      help="Enter age only if you do not wish to provide Date of Birth.")
                email = st.text_input("Email Address", max_chars=100,
                                      placeholder="e.g., john.doe@email.com")
                insurance = st.text_input(
                    "Health Insurance / TPA Details",
                    max_chars=120,
                    placeholder="e.g., Policy No. / TPA Name (optional)",
                )
                reason = st.text_area(
                    "Reason for Consultation (optional)",
                    max_chars=300,
                    placeholder="Brief reason for the visit (helps slot allocation)",
                    height=90,
                )

        # ---------------------------------------------------------------
        # Step 2: Appointment preference
        # ---------------------------------------------------------------
        st.markdown("#### 2️⃣ Appointment Preference")
        with st.container(border=True):
            dept_options = {d["name"]: d for d in departments}
            dept_name = st.selectbox("Select Department *", list(dept_options.keys()))

            selected_dept = dept_options[dept_name]
            doctors = booking_service.get_doctors_for_department(selected_dept["id"])
            doctor_names = [d["name"] for d in doctors] or ["General Consultation"]
            doctor_name = st.selectbox("Select Doctor *", doctor_names)

            min_date = dt.date.today()
            max_date = min_date + dt.timedelta(days=30)
            booking_date = st.date_input(
                "Preferred Date (Mon–Sat) *",
                value=None,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                help="OPD working hours: Mon–Sat, 8:00 AM – 4:00 PM. Sundays are closed.",
            )

            if booking_date is not None:
                if not booking_service.is_working_day(booking_date):
                    st.warning("OPD is closed on Sundays. Please choose a working day (Monday–Saturday).")
                    available_slots = []
                else:
                    available_slots = booking_service.generate_time_slots(booking_date)
            else:
                available_slots = []

            time_slot = st.selectbox(
                "Available Time Slots *",
                available_slots if available_slots else ["No slots available for selected date"],
                disabled=not available_slots,
            )

        # ---------------------------------------------------------------
        # Step 3: Confirm
        # ---------------------------------------------------------------
        st.markdown("#### 3️⃣ Review & Confirm")
        confirm_col1, confirm_col2 = st.columns([2, 1])
        with confirm_col2:
            submit_clicked = st.button("📌 Confirm Appointment", type="primary", use_container_width=True)

        if submit_clicked:
            # --- Client-side validation ---
            errors = []
            if not full_name.strip():
                errors.append("Full Name is required.")
            if not (dob or age > 0):
                errors.append("Please provide either a Date of Birth or a valid Age.")
            if len(phone.strip()) < 7:
                errors.append("Please provide a valid contact number (at least 7 digits).")
            if not id_number.strip():
                errors.append("Government Photo ID Number is required.")
            if booking_date is None:
                errors.append("Please select a preferred appointment date.")
            elif not booking_service.is_working_day(booking_date):
                errors.append("Selected date is a Sunday. OPD is closed — please pick a working day.")
            if not available_slots or time_slot == "No slots available for selected date":
                errors.append("No available time slot for the selected date. Please choose another day.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # --- Build booking record ---
                dob_str = dob.isoformat() if dob else f"Age: {int(age)}"
                patient_details = {
                    "full_name": full_name,
                    "dob": dob_str,
                    "gender": gender,
                    "phone": phone,
                    "email": email,
                    "id_type": id_type,
                    "id_number": id_number,
                    "insurance": insurance,
                    "reason": reason,
                    "department_id": selected_dept["id"],
                    "doctor_name": doctor_name,
                    "booking_date": booking_date.isoformat(),
                    "time_slot": time_slot,
                }

                try:
                    with st.spinner("Confirming your appointment..."):
                        booking = booking_service.create_booking(patient_details)
                    st.session_state.last_booking = booking

                    st.markdown(
                        f"""
                        <div class="portal-success">
                            <strong style="color:#047857;">✅ Appointment Confirmed!</strong><br>
                            A confirmation has been recorded. Please save your reference number.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.success(f"Reference Number: **{booking['reference_number']}**")

                    summary_col1, summary_col2 = st.columns(2)
                    with summary_col1:
                        st.markdown("##### 📋 Appointment Summary")
                        st.markdown(
                            f"""
                            | Field | Value |
                            |---|---|
                            | **Patient** | {booking['full_name']} |
                            | **Department** | {dept_name} |
                            | **Doctor** | {booking['doctor_name']} |
                            | **Date** | {booking['booking_date']} |
                            | **Time** | {booking['time_slot']} |
                            | **Status** | {booking['status']} ✅ |
                            """
                        )
                    with summary_col2:
                        st.markdown("##### 🧾 Patient Details")
                        st.markdown(
                            f"""
                            | Field | Value |
                            |---|---|
                            | **Gender** | {booking['gender']} |
                            | **DOB** | {booking['dob']} |
                            | **Phone** | {booking['phone']} |
                            | **Email** | {booking['email'] or '—'} |
                            | **ID Type** | {booking['id_type']} |
                            | **Insurance** | {booking['insurance']} |
                            """
                        )

                    st.info(
                        "📌 **Next Steps**: Please arrive at the hospital **15 minutes before** your "
                        "scheduled time and carry your Government Photo ID. If you need to reschedule, "
                        "call +1 (800) 555-0199 at least 24 hours in advance."
                    )

                except ValueError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    logger.error(f"Unexpected error while creating booking: {e}")
                    st.error("An unexpected error occurred while processing your booking. Please try again.")

# =============================================================================
# TAB 2: FIND MY BOOKING
# =============================================================================
with mode_tabs[1]:
    st.markdown("### 🔍 Find My Booking")
    st.caption("Enter the reference number you received at the time of booking.")

    ref_input = st.text_input("Reference Number (e.g., MC-20250210-A1B2)", max_chars=25)

    if st.button("🔎 Search Booking", use_container_width=False):
        if not ref_input.strip():
            st.warning("Please enter your reference number.")
        else:
            booking = booking_service.get_booking_by_reference(ref_input)
            if booking:
                st.success(f"Booking **{booking['reference_number']}** found!")
                st.markdown(
                    f"""
                    | Field | Value |
                    |---|---|
                    | **Patient** | {booking['full_name']} |
                    | **Department** | {booking['department_id'].replace('_', ' ').title()} |
                    | **Doctor** | {booking['doctor_name']} |
                    | **Date** | {booking['booking_date']} |
                    | **Time** | {booking['time_slot']} |
                    | **Status** | {booking['status']} ✅ |
                    | **Booked On** | {booking.get('created_at', '—')} |
                    """
                )
            else:
                st.error("No booking found with that reference number. Please double-check and try again.")

# =============================================================================
# TAB 3: CANCEL BOOKING
# =============================================================================
with mode_tabs[2]:
    st.markdown("### ✖️ Cancel Booking")
    st.caption("Cancel an existing appointment using its reference number.")

    cancel_ref = st.text_input("Reference Number to Cancel", max_chars=25, key="cancel_ref_input")

    confirm_cancel = st.checkbox("I understand that cancelling is final and the slot will be released to other patients.")

    if st.button("🗑️ Cancel Appointment", use_container_width=False):
        if not cancel_ref.strip():
            st.warning("Please enter your reference number.")
        elif not confirm_cancel:
            st.warning("Please confirm by ticking the cancellation acknowledgement checkbox.")
        else:
            cancelled = booking_service.cancel_booking(cancel_ref)
            if cancelled:
                st.success(f"Appointment **{cancel_ref.strip().upper()}** has been cancelled successfully.")
            else:
                st.error("No booking found with that reference number. Nothing was cancelled.")

# -----------------------------------------------------------------------------
# Footer disclaimer
# -----------------------------------------------------------------------------
st.markdown(
    f'<div class="disclaimer-footer"><strong>Legal Disclaimer:</strong> {MANDATORY_DISCLAIMER}</div>',
    unsafe_allow_html=True,
)

