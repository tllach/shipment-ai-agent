"""
Tests unitarios para RescheduleHandler — 5 casos.

NOTA sobre mocks:
- El handler usa `from agent.tools import get_shipment_status` → parchear: agent.reschedule.handler.get_shipment_status
- do_reschedule llama reschedule_shipment desde tool_reschedule → parchear: agent.reschedule.tool_reschedule.reschedule_shipment

No requiere Mock API ni Ollama corriendo.
"""

import pytest
from unittest.mock import patch
from agent.reschedule.handler import RescheduleHandler

# Fixtures

SHIPMENT_OK = {
    "success": True,
    "data": {
        "shipment_id": "14309635",
        "status": "IN_TRANSIT",
        "order_type": "Pickup",
        "origin": {},
        "destination": {},
        "cargo": {},
    },
}

SHIPMENT_DELIVERED = {
    "success": True,
    "data": {
        "shipment_id": "14324766",
        "status": "DELIVERED",
        "order_type": "Delivery",
        "origin": {},
        "destination": {},
        "cargo": {},
    },
}

SHIPMENT_NOT_FOUND = {
    "success": False,
    "not_found": True,
    "error": "No encontré ningún envío con el ID '00000000'.",
}

RESCHEDULE_SUCCESS = {
    "success": True,
    "updated": {"new_date": "2026-05-10", "time_window": "08:00-14:00"},
}

MOCK_STATUS  = "agent.reschedule.handler.get_shipment_status"
MOCK_RESCHEDULE = "agent.reschedule.tool_reschedule.reschedule_shipment"


def _make_handler() -> RescheduleHandler:
    return RescheduleHandler(config={})


# Caso 1 — Flujo completo sin pre-llenado

def test_flujo_completo_sin_prefill():
    """
    El usuario no da ningún dato. El handler recolecta todos los slots,
    confirma y ejecuta la reprogramación.
    """
    with patch(MOCK_STATUS, return_value=SHIPMENT_OK), \
         patch(MOCK_RESCHEDULE, return_value=RESCHEDULE_SUCCESS):

        h = _make_handler()

        r1 = h.handle("quiero reprogramar")
        assert "número de envío" in r1.lower()

        r2 = h.handle("14309635")
        assert "fecha" in r2.lower()

        r3 = h.handle("2026-05-10")
        assert "horario" in r3.lower()

        r4 = h.handle("08:00-14:00")
        assert "motivo" in r4.lower()

        r5 = h.handle("No estaré disponible")
        assert "confirma" in r5.lower() or "reprogramación" in r5.lower()
        assert "14309635" in r5
        assert "2026-05-10" in r5

        r6 = h.handle("SI")
        assert h.is_done()
        assert "2026-05-10" in r6 or "reprogramación" in r6.lower()


# Caso 2 — Pre-llenado desde el LLM con valores válidos

def test_prefill_valido_salta_slots():
    """
    Setear collected directamente con datos válidos debe saltarse esas
    preguntas e ir directo al motivo.
    """
    with patch(MOCK_STATUS, return_value=SHIPMENT_OK), \
         patch(MOCK_RESCHEDULE, return_value=RESCHEDULE_SUCCESS):

        h = _make_handler()
        # Simular lo que hace agent.py con prefill: setear collected directamente
        h.collected["shipment_id"] = "14309635"
        h.collected["new_date"]    = "2026-06-01"
        h.collected["time_window"] = "09:00-13:00"

        # El handler ya tiene shipment_id validado → al llamar handle(),
        # como current_slot es None, va directo a _next_turn() → pide motivo
        r1 = h.handle("quiero reprogramar el envío 14309635")
        assert "motivo" in r1.lower()

        r2 = h.handle("Cambio de agenda")
        assert "confirma" in r2.lower()
        assert "2026-06-01" in r2

        r3 = h.handle("SI")
        assert h.is_done()


# Caso 3 — Fecha inválida genera reintento

def test_fecha_invalida_genera_reintento():
    """
    Si el usuario escribe una fecha en formato incorrecto o pasada,
    el handler debe rechazarla y volver a pedir la fecha.
    """
    with patch(MOCK_STATUS, return_value=SHIPMENT_OK):
        h = _make_handler()

        h.handle("quiero reprogramar")  # pide ID
        h.handle("14309635")            # valida OK, pide fecha

        r = h.handle("el próximo lunes")   # fecha inválida
        assert "fecha" in r.lower()
        assert "new_date" not in h.collected or h.collected.get("new_date") is None


# Caso 4 — Envío DELIVERED bloquea la reprogramación

def test_envio_delivered_bloquea():
    """
    Un envío con status DELIVERED debe terminar el handler con mensaje
    de error antes de pedir fecha u otros datos.
    """
    with patch(MOCK_STATUS, return_value=SHIPMENT_DELIVERED):
        h = _make_handler()

        h.handle("quiero reprogramar")     # pide ID
        r = h.handle("14324766")           # valida → DELIVERED → bloquea

        assert h.is_done()
        assert "entregado" in r.lower() or "no puede reprogramarse" in r.lower()


# Caso 5 — Envío no encontrado termina sin pedir más datos

def test_envio_no_encontrado():
    """
    Si el shipment_id no existe en el API, el handler termina
    sin pedir fecha, horario ni motivo.
    """
    with patch(MOCK_STATUS, return_value=SHIPMENT_NOT_FOUND):
        h = _make_handler()

        h.handle("reprogramar")       # pide ID
        r = h.handle("00000000")      # 404 → termina

        assert h.is_done()
        assert "fecha" not in r.lower()
        assert "horario" not in r.lower()
        assert "00000000" in r or "no encontr" in r.lower()