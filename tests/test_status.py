"""
Tests de integración para StatusHandler.

NOTA sobre mocks: el handler importa con `from agent.tools import get_shipment_status`,
por lo que hay que parchear agent.status.handler.get_shipment_status (donde se usa),
no agent.tools.get_shipment_status (donde se define).
"""

import pytest
from unittest.mock import patch
from agent.status.handler import StatusHandler

# Fixtures

SHIPMENT_IN_TRANSIT = {
    "success": True,
    "data": {
        "shipment_id": "14309635",
        "status": "IN_TRANSIT",
        "order_type": "Pickup",
        "container": "UMXU 785234",
        "origin": {
            "name": "SUBARU OF AMERICA",
            "city": "LEBANON",
            "state": "IN",
            "date": "2025-01-02",
            "time": "07:30",
        },
        "destination": {
            "name": "CSXT - INDIANAPOLIS",
            "city": "AVON",
            "state": "IN",
            "date": "2026-12-31",
            "time": "17:00",
        },
        "cargo": {"weight_lbs": 10000, "pieces": 1, "bol": "98765", "seal": "S-112"},
    },
}

SHIPMENT_DELIVERED = {
    "success": True,
    "data": {
        "shipment_id": "14324766",
        "status": "DELIVERED",
        "order_type": "Delivery",
        "container": "",
        "origin": {"name": "ORIGEN", "city": "CHICAGO", "state": "IL", "date": "2025-06-01", "time": ""},
        "destination": {"name": "DESTINO", "city": "MIAMI", "state": "FL", "date": "2025-06-05", "time": ""},
        "cargo": {"weight_lbs": 500, "pieces": 2, "bol": "", "seal": ""},
    },
}

SHIPMENT_NOT_FOUND = {
    "success": False,
    "not_found": True,
    "error": "No encontré ningún envío con el ID '99999999'.",
}

API_ERROR = {
    "success": False,
    "not_found": False,
    "error": "No pude conectarme al sistema logístico.",
}

MOCK_PATH = "agent.status.handler.get_shipment_status"


def _make_handler(config=None) -> StatusHandler:
    return StatusHandler(config=config or {})


# Test 1 — Pide el ID si no viene pre-llenado

def test_pide_shipment_id_si_falta():
    """Sin pre-llenado el handler debe pedir el número de envío."""
    h = _make_handler()
    r = h.handle("quiero saber el estado de mi paquete")
    assert "envío" in r.lower() or "número" in r.lower()
    assert not h.is_done()


# Test 2 — Respuesta incluye estado y datos de envío

def test_respuesta_con_datos_completos():
    """
    Con shipment_id pre-llenado y API exitoso, la respuesta debe incluir
    el ID, el estado, origen y destino.
    """
    with patch(MOCK_PATH, return_value=SHIPMENT_IN_TRANSIT):
        h = _make_handler()
        h.collected["shipment_id"] = "14309635"

        r = h.handle("14309635")

        assert "14309635" in r
        assert "IN_TRANSIT" in r or "tránsito" in r.lower()
        assert "SUBARU OF AMERICA" in r
        assert "CSXT - INDIANAPOLIS" in r
        assert "10000" in r
        assert not h.is_done()        # espera follow-up
        assert h._waiting_followup


# Test 3 — Follow-up negativo → despedida
def test_followup_negativo_cierra_handler():
    """
    Después de mostrar el estado, si el usuario dice 'no gracias'
    el handler termina y devuelve mensaje de despedida.
    """
    with patch(MOCK_PATH, return_value=SHIPMENT_IN_TRANSIT):
        h = _make_handler()
        h.collected["shipment_id"] = "14309635"
        h.handle("14309635")           # muestra estado → _waiting_followup = True

        r = h.handle("no gracias")
        assert h.is_done()
        # El fallback es: "Si necesita algo más, no dude en escribirnos."
        assert any(w in r.lower() for w in ["placer", "hasta", "escribirnos", "ayud", "contacto"])


# Test 4 — Envío no encontrado

def test_envio_no_encontrado():
    """404 del API → mensaje de no encontrado y done=True."""
    with patch(MOCK_PATH, return_value=SHIPMENT_NOT_FOUND):
        h = _make_handler()
        h.collected["shipment_id"] = "99999999"

        r = h.handle("99999999")
        assert h.is_done()
        assert "99999999" in r or "no encontr" in r.lower()


# Test 5 — Envío entregado muestra "Entregado el"

def test_envio_entregado_muestra_fecha_entrega():
    """
    Para un envío DELIVERED el formatter debe mostrar
    'Entregado el' en lugar de 'Fecha estimada'.
    """
    with patch(MOCK_PATH, return_value=SHIPMENT_DELIVERED):
        h = _make_handler()
        h.collected["shipment_id"] = "14324766"

        r = h.handle("14324766")
        assert "Entregado el" in r
        assert "Fecha estimada" not in r


# Test 6 — Error de conexión al API termina el handler

def test_error_api_termina_handler():
    """Un error de conexión al API debe terminar el handler con mensaje de error."""
    with patch(MOCK_PATH, return_value=API_ERROR):
        h = _make_handler()
        h.collected["shipment_id"] = "14309635"

        r = h.handle("14309635")
        assert h.is_done()
        assert "error" in r.lower() or "conectar" in r.lower()


# Test 7 — Mensaje usa followup_question del YAML

def test_mensaje_usa_config_yaml():
    """
    Si el cliente tiene followup_question en su YAML,
    la respuesta debe incluir ese texto en lugar del fallback.
    """
    config = {
        "message_formats": {
            "followup_question": "¿Le puedo ayudar con algo más hoy?",
        }
    }
    with patch(MOCK_PATH, return_value=SHIPMENT_IN_TRANSIT):
        h = StatusHandler(config=config)
        h.collected["shipment_id"] = "14309635"

        r = h.handle("14309635")
        assert "¿Le puedo ayudar con algo más hoy?" in r