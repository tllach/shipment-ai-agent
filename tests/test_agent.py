"""
Tests de integración para el orquestador Agent.

Mockea:
    - agent.agent.detect_intent  → evita llamadas a Ollama
    - agent.status.handler.get_shipment_status
    - agent.reschedule.handler.get_shipment_status
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.agent import Agent

# Helpers

def _intent(intent, shipment_id=None, new_date=None, time_window=None, confidence="high"):
    return {
        "intent": intent,
        "shipment_id": shipment_id,
        "new_date": new_date,
        "time_window": time_window,
        "language": "es",
        "confidence": confidence,
    }

SHIPMENT_OK = {
    "success": True,
    "data": {
        "shipment_id": "14309635",
        "status": "IN_TRANSIT",
        "order_type": "Pickup",
        "container": "",
        "origin": {"name": "ORIGEN", "city": "CIUDAD", "state": "ST", "date": "2025-01-01", "time": ""},
        "destination": {"name": "DESTINO", "city": "CIUDAD2", "state": "ST2", "date": "2026-12-31", "time": ""},
        "cargo": {"weight_lbs": 100, "pieces": 1, "bol": "", "seal": ""},
    },
}

# Test 1 — GREETING devuelve bienvenida

def test_greeting_devuelve_bienvenida():
    """Un saludo debe activar el mensaje de bienvenida del cliente."""
    with patch("agent.agent.detect_intent", return_value=_intent("GREETING")):
        agent = Agent("cliente_a")
        r = agent.chat("hola")
        assert any(w in r.lower() for w in ["bienvenido", "hola", "ayud"])


# Test 2 — STATUS_QUERY con ID pre-llenado no vuelve a pedirlo

def test_status_query_con_id_prellenado():
    """
    Si detect_intent extrae un shipment_id que aparece en el mensaje,
    el handler no debe volver a pedirlo.
    """
    with patch("agent.agent.detect_intent",
               return_value=_intent("STATUS_QUERY", shipment_id="14309635")), \
         patch("agent.status.handler.get_shipment_status", return_value=SHIPMENT_OK):

        agent = Agent("cliente_a")
        r = agent.chat("estado del envío 14309635")

        assert "14309635" in r
        assert "número de envío" not in r.lower()


# Test 3 — Guardia anti-alucinación

def test_guardia_anti_alucinacion():
    """
    Si el LLM extrae un shipment_id que NO aparece literalmente en el
    mensaje, el orquestador lo descarta y el handler pide el ID.
    """
    with patch("agent.agent.detect_intent",
               return_value=_intent("STATUS_QUERY", shipment_id="14309635")):

        agent = Agent("cliente_a")
        r = agent.chat("quiero saber el estado de mi paquete")

        assert "número" in r.lower() or "envío" in r.lower()
        assert "14309635" not in r


# Test 4 — CANCEL sin handler activo

def test_cancel_sin_handler_activo():
    """CANCEL sin handler activo debe devolver cancel_confirmation."""
    with patch("agent.agent.detect_intent", return_value=_intent("CANCEL")):
        agent = Agent("cliente_a")
        r = agent.chat("cancelar")
        assert any(w in r.lower() for w in ["cancelad", "operación", "ayud"])


# Test 5 — UNKNOWN escala tras N intentos

def test_unknown_escala_tras_n_intentos():
    """
    cliente_a tiene escalate_after_attempts: 2.
    Dos UNKNOWN seguidos deben escalar a agente humano.
    """
    with patch("agent.agent.detect_intent", return_value=_intent("UNKNOWN")):
        agent = Agent("cliente_a")

        r1 = agent.chat("¿cuánto cuesta enviar?")
        assert "escalad" not in r1.lower()

        r2 = agent.chat("¿tienen oficina en Bogotá?")
        assert any(w in r2.lower() for w in ["agente", "humano", "escalad", "conectar"])


# Test 6 — reset() limpia el estado completo

def test_reset_limpia_handler_activo():
    """reset() debe limpiar el handler activo, historial y contadores."""
    with patch("agent.agent.detect_intent",
               return_value=_intent("STATUS_QUERY", shipment_id=None)):

        agent = Agent("cliente_a")
        agent.chat("quiero saber el estado")

        assert agent.active_handler is not None

        agent.reset()
        assert agent.active_handler is None
        assert agent.history == []
        assert agent._unknown_count == 0


# Test 7 — Handler activo recibe turnos sin re-detectar intención

def test_handler_activo_recibe_continuacion():
    """
    Una vez activado un handler, los mensajes siguientes van al handler
    sin volver a llamar detect_intent.
    """
    detect_mock = MagicMock(return_value=_intent("STATUS_QUERY", shipment_id=None))

    with patch("agent.agent.detect_intent", detect_mock), \
         patch("agent.status.handler.get_shipment_status", return_value=SHIPMENT_OK):

        agent = Agent("cliente_a")
        agent.chat("quiero el estado")    # turno 1 → llama detect_intent
        agent.chat("14309635")            # turno 2 → va al handler, no llama detect_intent

        assert detect_mock.call_count == 1


# Test 8 — RESCHEDULE con slots en el mensaje va directo al motivo

def test_reschedule_con_slots_en_mensaje():
    """
    Con shipment_id, new_date y time_window presentes en el mensaje,
    el orquestador los pre-llena y el handler pide solo el motivo.
    """
    with patch("agent.agent.detect_intent",
               return_value=_intent("RESCHEDULE",
                                    shipment_id="14309635",
                                    new_date="2026-06-15",
                                    time_window="08:00-12:00")), \
         patch("agent.reschedule.handler.get_shipment_status", return_value=SHIPMENT_OK):

        agent = Agent("cliente_a")
        msg = "reprogramar envío 14309635 para el 2026-06-15 de 08:00-12:00"
        r = agent.chat(msg)

        assert "motivo" in r.lower()