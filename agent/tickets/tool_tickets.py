import requests
from typing import Optional
import re


EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
API_BASE = "http://localhost:8000"

# Valid values (mirrors API validation)
VALID_ISSUE_TYPES = {
    "DAÑO",
    "RETRASO",
    "PEDIDO_FALTANTE",
    "ENTREGA_ERRÓNEA",
    "FACTURACIÓN",
    "OTROS",
}

# Slot definition
# Each slot has: key, question to ask user, required flag, validator (optional)
TICKET_SLOTS = [
    {
        "key": "shipment_id",
        "question": "Por favor, proporcione su ID de envío para que podamos localizar su pedido.",
        "required": True,
    },
    {
        "key": "issue_type",
        "question": (
            "¿Qué tipo de problema está experimentando?\n"
            "Opciones: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS"
        ),
        "required": True,
        "validator": lambda v: v.upper() in VALID_ISSUE_TYPES,
        "error": "Por favor escoja entre los siguientes: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS.",
    },
    {
        "key": "description",
        "question": "Por favor, describa el problema en detalle.",
        "validator": lambda v: len(v.strip()) > 15,
        "error": "La descripción es muy corta. Por favor, proporcione más detalles sobre el problema.",
        "required": True,
    },
    {
        "key": "contact_email",
        "question": "¿Cuál es su dirección de correo electrónico para que podamos seguir con usted?",
        "validator": lambda v: re.match(EMAIL_REGEX, v),
        "error": "Por favor, ingrese una dirección de correo electrónico válida.",
        "required": True,
    },
]


# Slot filling helpers 

def get_next_missing_slot(collected: dict) -> Optional[dict]:
    """Return the next slot that still needs to be filled."""
    for slot in TICKET_SLOTS:
        key = slot["key"]
        if key not in collected or collected[key] is None:
            if slot.get("required", False):
                return slot
            # Non-required: only ask if not yet attempted
            if key not in collected:
                return slot
    return None


def validate_slot(slot: dict, value: str) -> tuple[bool, str]:
    """Validate a slot value. Returns (is_valid, error_message)."""
    validator = slot.get("validator")
    if validator and not validator(value):
        return False, slot.get("error", "Invalid value.")
    return True, ""


def fill_slot(collected: dict, slot_key: str, value: str) -> tuple[bool, str]:
    """
    Try to fill a specific slot with the given value.
    Returns (success, error_message).
    """
    slot = next((s for s in TICKET_SLOTS if s["key"] == slot_key), None)
    if not slot:
        return False, f"Unknown slot '{slot_key}'."

    valid, error = validate_slot(slot, value)
    if not valid:
        return False, error

    collected[slot_key] = value
    return True, ""


def apply_defaults(collected: dict) -> dict:
    """Fill in defaults for any non-required, unanswered slots."""
    for slot in TICKET_SLOTS:
        key = slot["key"]
        if key not in collected and not slot.get("required", False):
            default = slot.get("default")
            if default:
                collected[key] = default
    return collected


# API calls

def create_ticket(slots: dict) -> dict:
    """ Call POST /tickets with the collected slots. Returns the API response dict or raises on error. """
    slots = apply_defaults(slots)
    
    payload = {
        "shipment_id": slots["shipment_id"],
        "issue_type": slots["issue_type"].upper(),
        "description": slots["description"],
        "contact_email": slots.get("contact_email"),
        "contact_phone": slots.get("contact_phone"),
    }
    try:
        resp = requests.post(f"{API_BASE}/tickets", json=payload, timeout=5)
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No se pudo conectar al sistema. Intente más tarde."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"success": False, "error": detail}


def get_tickets_for_shipment(shipment_id: str) -> dict:
    """
    Call GET /tickets?shipment_id=... to retrieve existing tickets.
    """
    try:
        resp = requests.get(
            f"{API_BASE}/tickets",
            params={"shipment_id": shipment_id},
            timeout=5,
        )
        if resp.status_code == 404:
            return {"success": True, "data": []}   # 404 = sin tickets, no es error
        
        resp.raise_for_status()
        data = resp.json()
        tickets = data.get("tickets", data) if isinstance(data, dict) else data
        return {"success": True, "data": tickets}
    
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No se pudo conectar al sistema."}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": str(e)}
