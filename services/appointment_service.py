# hospital-information-assistant/services/appointment_service.py

from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("AppointmentService")


class AppointmentService:
    """
    Handles appointment guidance, workflow generation, and booking
    preparation information for hospital outpatients.
    """

    def get_general_appointment_workflow(self) -> Dict[str, Any]:
        """
        Returns the standard outpatient appointment guidance workflow
        including booking options, required information, preparation
        checklist, and cancellation/rescheduling policy.
        """
        logger.info("Returning general appointment workflow data.")

        return {
            "booking_options": [
                {
                    "mode": "📞 Phone Booking",
                    "details": "Call the OPD reception at +1 (800) 555-0199 during working hours (Mon–Sat, 8:00 AM – 4:00 PM)."
                },
                {
                    "mode": "🏥 Walk-In Registration",
                    "details": "Visit the OPD Registration Desk at Block A, Ground Floor. Carry a valid government photo ID."
                },
                {
                    "mode": "🌐 Online Portal",
                    "details": "Book via the hospital website: https://www.metrocarehospital.org/appointments"
                }
            ],
            "required_information": [
                "Full Name (as per government-issued ID)",
                "Date of Birth / Age",
                "Contact Number (preferably mobile)",
                "Valid Government Photo ID (Passport / Driver's License / National ID)",
                "Health Insurance Card or TPA details (if applicable)",
                "Brief reason for consultation (optional, for slot allocation)"
            ],
            "preparation_checklist": [
                "Carry your previous medical records and current medication list.",
                "Reach the hospital at least 15 minutes before your scheduled appointment time.",
                "Wear comfortable clothing — especially if you need a physical examination.",
                "Arrange for a companion if you require assistance during the visit.",
                "Keep your insurance card and photo ID easily accessible.",
                "If fasting is required for any blood tests, follow the instructions provided during booking."
            ],
            "cancellation_and_rescheduling": (
                "To cancel or reschedule an appointment, please call the OPD reception "
                "at +1 (800) 555-0199 at least 24 hours before the scheduled time. "
                "Walk-in cancellations are also accepted at the OPD Registration Desk. "
                "Repeated no-shows may affect future priority booking eligibility."
            )
        }


# Module-level singleton instance for convenience
appointment_service = AppointmentService()

