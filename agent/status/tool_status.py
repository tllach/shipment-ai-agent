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


# Response formatter

STATUS_LABEL = {
    "DELIVERED":         "Entregado",
    "IN_TRANSIT":        "En tránsito",
    "PICKED_UP":         "Recolectado",
    "SCHEDULED_PICKUP":  "Recolección programada",
    "PENDING_SCHEDULE":  "Pendiente de programar",
    "TRANSFERRED":       "Transferido",
    "UNKNOWN":           "Estado desconocido",
}


def _days_until(date_str: str) -> str:
    """Calcula cuántos días faltan o pasaron desde hoy."""
    from datetime import datetime, date
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        delta  = (target - date.today()).days
        if delta == 0:
            return " (hoy)"
        elif delta == 1:
            return " (mañana)"
        elif delta > 1:
            return f" (en {delta} días)"
        elif delta == -1:
            return " (ayer)"
        else:
            return f" (hace {abs(delta)} días)"
    except ValueError:
        return ""


def format_status_response(data: dict) -> str:
    """
    Convierte la respuesta del API en un mensaje legible para el usuario.
    NUNCA inventa datos — si un campo está vacío, no lo muestra.
    """
    sid        = data.get("shipment_id", "N/A")
    status     = data.get("status", "UNKNOWN")
    label      = STATUS_LABEL.get(status, status)
    order_type = data.get("order_type", "")
    origin     = data.get("origin", {})
    destination= data.get("destination", {})
    cargo      = data.get("cargo", {})
    container  = data.get("container", "")

    lines = [
        f"Estado del envío {sid}",
        f"Estado: {label}",
    ]

    if order_type:
        lines.append(f"Tipo de operación: {order_type}")

    if container:
        lines.append(f"Contenedor: {container}")

    # Origen
    if origin.get("name"):
        o = origin["name"]
        if origin.get("city") and origin.get("state"):
            o += f" — {origin['city']}, {origin['state']}"
        if origin.get("date"):
            t = f" a las {origin['time']}" if origin.get("time") else ""
            rel = _days_until(origin['date'])
            o += f"\n {origin['date']}{t}{rel}"
        lines.append(f"Origen: {o}")

    # Destino
    if destination.get("name"):
        d = destination["name"]
        if destination.get("city") and destination.get("state"):
            d += f" — {destination['city']}, {destination['state']}"
        if destination.get("date"):
            t = f" a las {destination['time']}" if destination.get("time") else ""
            rel = _days_until(destination['date'])
            if status == "DELIVERED":
                d += f"\n Entregado el {destination['date']}{t}"
            else:
                d += f"\n Fecha estimada: {destination['date']}{t}{rel}"
        lines.append(f"Destino: {d}")

    # Carga
    cargo_parts = []
    if cargo.get("pieces"):
        cargo_parts.append(f"{cargo['pieces']} piezas")
    if cargo.get("weight_lbs"):
        cargo_parts.append(f"{cargo['weight_lbs']} lbs")
    if cargo_parts:
        lines.append(f"Carga: {', '.join(cargo_parts)}")

    # Referencia documental
    refs = []
    if cargo.get("bol"):
        refs.append(f"BOL: {cargo['bol']}")
    if cargo.get("seal"):
        refs.append(f"Sello: {cargo['seal']}")
    if refs:
        lines.append(" | ".join(refs))

    return "\n".join(lines)