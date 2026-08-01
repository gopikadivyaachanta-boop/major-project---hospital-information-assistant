# hospital-information-assistant/services/booking_service.py

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger("BookingService")

# Working hours for OPD (Mon-Sat, 8:00 AM - 4:00 PM)
BOOKING_START_HOUR = 8
BOOKING_END_HOUR = 16  # 4:00 PM (exclusive)
SLOT_MINUTES = 30
WORKING_DAYS = [0, 1, 2, 3, 4, 5]  # Monday = 0 ... Saturday = 5


class BookingService:
    """
    Handles online OPD appointment booking: loads departments/doctors from the
    hospital knowledge base, manages time-slot availability, and persists
    patient appointments to a local JSON store.
    """

    def __init__(self, data_file: Optional[Path] = None, bookings_file: Optional[Path] = None):
        self.data_file = data_file or (DATA_DIR / "hospital_data.json")
        self.bookings_file = bookings_file or (DATA_DIR / "appointments.json")
        self._hospital_data: Optional[Dict[str, Any]] = None
        self._bookings: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_hospital_data(self) -> Dict[str, Any]:
        """Loads hospital data JSON (departments, doctors, etc.)."""
        if self._hospital_data is not None:
            return self._hospital_data

        if not self.data_file.exists():
            logger.error(f"Hospital data file not found at {self.data_file}")
            raise FileNotFoundError(f"Missing hospital data file: {self.data_file}")

        with open(self.data_file, "r", encoding="utf-8") as f:
            self._hospital_data = json.load(f)
        return self._hospital_data

    def _load_bookings(self) -> List[Dict[str, Any]]:
        """Loads the persisted appointment store (creates empty file if missing)."""
        if self._bookings is not None:
            return self._bookings

        if not self.bookings_file.exists():
            logger.info(f"No bookings file found. Creating empty store at {self.bookings_file}")
            self.bookings_file.write_text("[]", encoding="utf-8")
            self._bookings = []
            return self._bookings

        try:
            with open(self.bookings_file, "r", encoding="utf-8") as f:
                self._bookings = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read bookings file ({e}). Starting with empty store.")
            self._bookings = []
        return self._bookings

    def _save_bookings(self) -> None:
        """Persists the current in-memory bookings list to disk."""
        with open(self.bookings_file, "w", encoding="utf-8") as f:
            json.dump(self._bookings, f, indent=2, default=str)
        logger.info(f"Saved {len(self._bookings)} bookings to {self.bookings_file}")

    # ------------------------------------------------------------------
    # Reference number generation
    # ------------------------------------------------------------------
    def generate_reference_number(self) -> str:
        """Generates a unique, human-friendly appointment reference code."""
        today = date.today()
        code = uuid.uuid4().hex[:4].upper()
        ref = f"MC-{today.strftime('%Y%m%d')}-{code}"

        # Ensure uniqueness against persisted bookings
        existing = {b.get("reference_number") for b in self._load_bookings()}
        while ref in existing:
            code = uuid.uuid4().hex[:4].upper()
            ref = f"MC-{today.strftime('%Y%m%d')}-{code}"
        return ref

    # ------------------------------------------------------------------
    # Slot generation & availability
    # ------------------------------------------------------------------
    def get_departments(self) -> List[Dict[str, Any]]:
        """Returns the list of departments for the booking dropdowns."""
        return self._load_hospital_data().get("departments", [])

    def get_doctors_for_department(self, dept_id: str) -> List[Dict[str, Any]]:
        """Returns doctors for a given department id."""
        for dept in self.get_departments():
            if dept.get("id") == dept_id:
                return dept.get("doctors", [])
        return []

    def generate_time_slots(self, booking_date: date) -> List[str]:
        """
        Generates available (unbooked) 30-minute slots for a given date.
        OPD hours are Mon-Sat, 8:00 AM - 4:00 PM.
        """
        if not self.is_working_day(booking_date):
            return []

        booked_slots = {
            b.get("time_slot")
            for b in self._load_bookings()
            if b.get("booking_date") == booking_date.isoformat()
        }

        slots = []
        slot_time = datetime.combine(booking_date, datetime.min.time()).replace(hour=BOOKING_START_HOUR)
        end_time = slot_time.replace(hour=BOOKING_END_HOUR)

        while slot_time < end_time:
            slot_label = slot_time.strftime("%I:%M %p")
            if slot_label not in booked_slots:
                slots.append(slot_label)
            slot_time += timedelta(minutes=SLOT_MINUTES)

        return slots

    def is_working_day(self, booking_date: date) -> bool:
        """Returns True if the date is a working OPD day (Mon-Sat)."""
        return booking_date.weekday() in WORKING_DAYS

    # ------------------------------------------------------------------
    # Booking creation
    # ------------------------------------------------------------------
    def create_booking(self, patient_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and stores a new appointment booking.

        patient_details expects keys:
            full_name, dob, gender, phone, email, id_type, id_number,
            insurance, department_id, doctor_name, booking_date (iso str), time_slot
        """
        bookings = self._load_bookings()
        department_id = patient_details.get("department_id")
        doctor_name = patient_details.get("doctor_name")
        booking_date = patient_details.get("booking_date")
        time_slot = patient_details.get("time_slot")

        # --- Validation ---
        if not department_id:
            raise ValueError("Please select a department.")
        if not doctor_name:
            raise ValueError("Please select a doctor.")
        if not booking_date:
            raise ValueError("Please select a preferred appointment date.")
        if not time_slot:
            raise ValueError("Please select a time slot.")

        # Slot availability check (double-booking prevention)
        slot_taken = any(
            b.get("booking_date") == booking_date and b.get("time_slot") == time_slot
            for b in bookings
        )
        if slot_taken:
            raise ValueError(
                f"Sorry, the slot on {booking_date} at {time_slot} is already booked. "
                "Please choose another time slot or date."
            )

        # Build booking record
        booking = {
            "reference_number": self.generate_reference_number(),
            "full_name": patient_details.get("full_name", "").strip(),
            "dob": patient_details.get("dob"),
            "gender": patient_details.get("gender", ""),
            "phone": patient_details.get("phone", "").strip(),
            "email": patient_details.get("email", "").strip(),
            "id_type": patient_details.get("id_type", ""),
            "id_number": patient_details.get("id_number", "").strip(),
            "insurance": patient_details.get("insurance", "").strip() or "Not Provided",
            "department_id": department_id,
            "doctor_name": doctor_name,
            "booking_date": booking_date,
            "time_slot": time_slot,
            "created_at": datetime.now().isoformat(),
            "status": "Confirmed",
        }

        bookings.append(booking)
        self._save_bookings()
        logger.info(f"New booking created: {booking['reference_number']} for {booking['full_name']}")
        return booking

    # ------------------------------------------------------------------
    # Booking lookup
    # ------------------------------------------------------------------
    def get_booking_by_reference(self, reference_number: str) -> Optional[Dict[str, Any]]:
        """Finds a booking by its unique reference number."""
        ref = reference_number.strip().upper()
        for b in self._load_bookings():
            if b.get("reference_number", "").upper() == ref:
                return b
        return None

    def cancel_booking(self, reference_number: str) -> bool:
        """Cancels (removes) a booking by reference number. Returns True on success."""
        bookings = self._load_bookings()
        ref = reference_number.strip().upper()
        for i, b in enumerate(bookings):
            if b.get("reference_number", "").upper() == ref:
                removed = bookings.pop(i)
                self._save_bookings()
                logger.info(f"Cancelled booking {removed['reference_number']}")
                return True
        return False


# Module-level singleton instance for convenience
booking_service = BookingService()

