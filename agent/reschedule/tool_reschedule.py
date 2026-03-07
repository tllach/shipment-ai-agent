import requests
from typing import Optional
from datetime import datetime

from agent.tools import reschedule_shipment, get_shipment_status

API_BASE = "http://localhost:8000"

#  Validadores 

def _valid_date(v: str) -> bool:
    """Valida formato YYYY-MM-DD y que no sea fecha pasada."""
    try:
        d = datetime.strptime(v.strip(), "%Y-%m-%d").date()
        return d >= datetime.today().date()
    except ValueError:
        return False

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


# Slot definition

RESCHEDULE_SLOTS = [
    {
        "key": "shipment_id",
        "question": "¿Cuál es el número de envío que deseas reprogramar?",
        "required": True,
        "validator": lambda v: bool(get_shipment_status(v).get("success", False)),
        "error": "No encontré un envío con ese ID. Por favor verifica el número e intenta de nuevo.",
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