"""Clinic appointments API (fixture). Contains seeded defects — do not fix here;
this file exists to test whether a park run predicts them. See truth.json."""

DB = {
    "users": {
        "u1": {"clinic": "A", "role": "staff"},
        "u2": {"clinic": "B", "role": "staff"},
        "u3": {"clinic": "A", "role": None},  # legacy row, role never backfilled
    },
    "appointments": {
        "ap1": {"clinic": "A", "patient": "p1", "status": "booked"},
        "ap2": {"clinic": "B", "patient": "p9", "status": "booked"},
    },
}


def get_appointment(user_id: str, appointment_id: str):
    """Fetch an appointment for the dashboard."""
    user = DB["users"][user_id]
    appt = DB["appointments"].get(appointment_id)
    if appt is None:
        return {"error": "not found"}
    # BUG-1 (seeded): no tenant check — any valid user can read any clinic's
    # appointment by guessing/iterating ids (IDOR across clinics).
    return {"id": appointment_id, **appt}


def cancel_appointment(user_id: str, appointment_id: str, is_admin_ui: bool):
    """Cancel from the admin screen. The cancel button is hidden for
    non-admins in the UI."""
    appt = DB["appointments"].get(appointment_id)
    if appt is None:
        return {"error": "not found"}
    # BUG-2 (seeded): authorization trusts a client-supplied flag; the server
    # never re-derives the role, so a direct API call cancels anything.
    if is_admin_ui:
        appt["status"] = "cancelled"
        return {"ok": True}
    return {"error": "forbidden"}


def can_export(user_id: str) -> bool:
    """Only staff may export patient data."""
    role = DB["users"][user_id]["role"]
    # BUG-3 (seeded): unknown/None role falls through to allow — fails open
    # for legacy rows that never got a role backfill.
    if role == "patient":
        return False
    return True
