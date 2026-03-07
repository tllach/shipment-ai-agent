
from typing import Optional

API_BASE = "http://localhost:8000"

# Slot definition
STATUS_SLOTS = [
    {
        "key": "shipment_id",
        "question": "¿Cuál es el número de envío que deseas consultar?",
        "required": True,
    }
]

# Slot helpers 

def get_next_missing_slot(collected: dict) -> Optional[dict]:
    """Retorna el siguiente slot requerido que falta por llenar."""
    for slot in STATUS_SLOTS:
        if slot["key"] not in collected or collected[slot["key"]] is None:
            return slot
    return None


def fill_slot(collected: dict, slot_key: str, value: str) -> tuple[bool, str]:
    """Llena un slot con el valor dado. Retorna (éxito, mensaje_error)."""
    slot = next((s for s in STATUS_SLOTS if s["key"] == slot_key), None)
    if not slot:
        return False, f"Slot desconocido: '{slot_key}'."
    collected[slot_key] = value.strip()
    return True, ""


# API call


# Response formatter

STATUS_EMOJI = {
    "DELIVERED":         "✅",
    "IN_TRANSIT":        "🚚",
    "PICKED_UP":         "📦",
    "SCHEDULED_PICKUP":  "📋",
    "PENDING_SCHEDULE":  "⏳",
    "TRANSFERRED":       "🔄",
    "UNKNOWN":           "❓",
}

STATUS_LABEL = {
    "DELIVERED":         "Entregado",
    "IN_TRANSIT":        "En tránsito",
    "PICKED_UP":         "Recolectado",
    "SCHEDULED_PICKUP":  "Recolección programada",
    "PENDING_SCHEDULE":  "Pendiente de programar",
    "TRANSFERRED":       "Transferido",
    "UNKNOWN":           "Estado desconocido",
}


def format_status_response(data: dict) -> str:
    """
    Convierte la respuesta del API en un mensaje legible para el usuario.
    NUNCA inventa datos — si un campo está vacío, no lo muestra.
    """
    sid        = data.get("shipment_id", "N/A")
    status     = data.get("status", "UNKNOWN")
    emoji      = STATUS_EMOJI.get(status, "❓")
    label      = STATUS_LABEL.get(status, status)
    order_type = data.get("order_type", "")
    origin     = data.get("origin", {})
    destination= data.get("destination", {})
    cargo      = data.get("cargo", {})
    
    

    lines = [
        f"Estado del envío {sid}",
        f"Estado: {label} {emoji}",
    ]

    if order_type:
        lines.append(f"Tipo de operación: {order_type}")

    # Origen
    if origin.get("name"):
        o = origin["name"]
        if origin.get("city") and origin.get("state"):
            o += f" — {origin['city']}, {origin['state']}"
        if origin.get("date"):
            t = f" a las {origin['time']}" if origin.get("time") else ""
            o += f"\n {origin['date']}{t}"
        lines.append(f"Origen: {o}")

    # Destino
    if destination.get("name"):
        d = destination["name"]
        if destination.get("city") and destination.get("state"):
            d += f" — {destination['city']}, {destination['state']}"
        if destination.get("date"):
            t = f" a las {destination['time']}" if destination.get("time") else ""
            
            if(status == "DELIVERED"):
                d += f"\n Entregado el {destination['date']}{t}"
            else:
                d += f"\n Fecha estimada: {destination['date']}{t}"
        lines.append(f"Destino: {d}")

    # Carga
    cargo_parts = []
    if cargo.get("weight_lbs"):
        cargo_parts.append(f"{cargo['weight_lbs']} lbs")
    if cargo.get("pieces"):
        cargo_parts.append(f"{cargo['pieces']} piezas")
    if cargo_parts:
        lines.append(f"Carga: {', '.join(cargo_parts)}")

    lines.append("\n¿Necesitas hacer algo más con este envío?")
    return "\n".join(lines)
