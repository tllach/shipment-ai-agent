import requests
from typing import Optional
from datetime import datetime

from agent.tools import reschedule_shipment, get_shipment_status

API_BASE = "http://localhost:8000"

#  Validadores 

NON_RESCHEDULABLE_STATUSES = {"DELIVERED", "TRANSFERRED"}

def _valid_date(v: str) -> bool:
    """Valida formato YYYY-MM-DD y que no sea fecha pasada."""
    try:
        d = datetime.strptime(v.strip(), "%Y-%m-%d").date()
        return d >= datetime.today().date()
    except ValueError:
        return False


def _normalize_time(t: str) -> str:
    """
    Normaliza un tiempo HH:MM o H:MM a formato HH:MM con cero padding.
    Ej: "8:00" → "08:00", "08:00" → "08:00"
    """
    t = t.strip()
    parts = t.split(":")
    if len(parts) == 2:
        return f"{int(parts[0]):02d}:{parts[1].zfill(2)}"
    return t


def _valid_time_window(v: str) -> bool:
    """Valida formato HH:MM-HH:MM (ej: 08:00-12:00)."""
    try:
        parts = v.strip().split("-")
        if len(parts) != 2:
            return False
        datetime.strptime(parts[0].strip(), "%H:%M")
        datetime.strptime(parts[1].strip(), "%H:%M")
        return True
    except ValueError:
        return False


def normalize_time_window(v: str) -> str:
    """
    Normaliza un time_window completo a formato estándar HH:MM-HH:MM.
    Ej: "8:00-12:00" → "08:00-12:00"
    """
    try:
        parts = v.strip().split("-")
        if len(parts) == 2:
            return f"{_normalize_time(parts[0])}-{_normalize_time(parts[1])}"
    except Exception:
        pass
    return v


def days_until(date_str: str) -> str:
    """Retorna texto relativo: '(en 3 días)', '(hoy)', '(mañana)'."""
    try:
        from datetime import date
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        delta  = (target - date.today()).days
        if delta == 0:   return " (hoy)"
        if delta == 1:   return " (mañana)"
        if delta > 1:    return f" (en {delta} días)"
        if delta == -1:  return " (ayer)"
        return f" (hace {abs(delta)} días)"
    except ValueError:
        return ""

# Slot definition

RESCHEDULE_SLOTS = [
    {
        "key": "shipment_id",
        "question": "¿Cuál es el número de envío que deseas reprogramar?",
        "required": True,
    },
    {
        "key": "new_date",
        "question": "¿Cuál es la nueva fecha para el envío? (formato: YYYY-MM-DD, ej: 2025-04-15)",
        "required": True,
        "validator": _valid_date,
        "error": "La fecha no es válida o ya pasó. Usa el formato YYYY-MM-DD con una fecha futura.",
    },
    {
        "key": "time_window",
        "question": "¿En qué horario? (formato: HH:MM-HH:MM, ej: 08:00-12:00)",
        "required": True,
        "validator": _valid_time_window,
        "error": "El formato de horario no es válido. Usa HH:MM-HH:MM (ej: 08:00-12:00).",
    },
    {
        "key": "reason",
        "question": "¿Cuál es el motivo de la reprogramación?",
        "required": True,
        "validator": lambda v: len(v.strip()) > 5,
        "error": "Por favor proporciona un motivo más descriptivo.",
    },
]


# Slot helpers

def get_next_missing_slot(collected: dict) -> Optional[dict]:
    """Retorna el siguiente slot requerido que falta por llenar."""
    for slot in RESCHEDULE_SLOTS:
        key = slot["key"]
        if key not in collected or collected[key] is None:
            return slot
    return None


def validate_slot(slot: dict, value: str) -> tuple[bool, str]:
    """Valida un valor contra el slot. Retorna (válido, mensaje_error)."""
    validator = slot.get("validator")
    if validator and not validator(value):
        return False, slot.get("error", "Valor inválido.")
    return True, ""


def fill_slot(collected: dict, slot_key: str, value: str) -> tuple[bool, str]:
    """Llena un slot validando el valor. Retorna (éxito, mensaje_error)."""
    slot = next((s for s in RESCHEDULE_SLOTS if s["key"] == slot_key), None)
    if not slot:
        return False, f"Slot desconocido: '{slot_key}'."
    valid, error = validate_slot(slot, value)
    if not valid:
        return False, error
    collected[slot_key] = value.strip()
    return True, ""


#  API call 

def do_reschedule(slots: dict) -> dict:
    """
    Llama a POST /shipments/{id}/reschedule.
    Retorna dict con success + data o error.
    """
    return reschedule_shipment(
        shipment_id=slots["shipment_id"],
        new_date=slots["new_date"],
        time_window=slots["time_window"],
        reason=slots.get("reason"),
    )