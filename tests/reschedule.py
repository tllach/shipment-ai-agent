import pytest
from unittest.mock import patch

from agent.reschedule.handler import RescheduleHandler


# Test 1: flujo completo exitoso

@patch("agent.reschedule.handler.do_reschedule")
@patch("agent.reschedule.handler.fill_slot")
@patch("agent.reschedule.handler.get_next_missing_slot")
def test_reschedule_success(
    mock_next_slot,
    mock_fill_slot,
    mock_do_reschedule,
):

    handler = RescheduleHandler()

    mock_next_slot.side_effect = [
        {"key": "shipment_id", "question": "ID?"},
        {"key": "new_date", "question": "Fecha?"},
        {"key": "time_window", "question": "Horario?"},
        {"key": "reason", "question": "Motivo?"},
        None
    ]

    mock_fill_slot.return_value = (True, "")

    mock_do_reschedule.return_value = {
        "success": True,
        "updated": {
            "new_date": "2025-03-10",
            "time_window": "MORNING"
        }
    }

    r1 = handler.handle("hola")
    r2 = handler.handle("143")
    r3 = handler.handle("2025-03-10")
    r4 = handler.handle("mañana")
    r5 = handler.handle("no estoy en casa")

    assert handler.awaiting_confirmation

    r6 = handler.handle("si")

    assert handler.is_done()
    assert "reprogramación realizada" in r6.lower()


# Test 2: cancelación

def test_cancel_reschedule():

    handler = RescheduleHandler()

    response = handler.handle("cancelar")

    assert handler.is_done()
    assert "cancelado" in response.lower()


# Test 3: edición de campo

def test_edit_flow():

    handler = RescheduleHandler()

    handler.collected = {
        "shipment_id": "143",
        "new_date": "2025-03-10",
        "time_window": "MORNING",
        "reason": "no estoy en casa",
    }

    handler.awaiting_confirmation = True

    r1 = handler.handle("no")

    assert handler.awaiting_edit_choice
    assert "corregir" in r1.lower()

    r2 = handler.handle("1")

    assert handler.editing_slot == "new_date"


# Test 4: retry cuando slot falla

@patch("agent.reschedule.handler.fill_slot")
def test_slot_retry(mock_fill_slot):

    handler = RescheduleHandler()

    handler.current_slot = {
        "key": "new_date",
        "question": "Fecha?"
    }

    mock_fill_slot.return_value = (False, "Fecha inválida")

    r1 = handler.handle("ayer")

    assert "fecha inválida" in r1.lower()
    assert handler.attempts["new_date"] == 1


# Test 5: confirmación negativa

def test_confirmation_negative():

    handler = RescheduleHandler()

    handler.collected = {
        "shipment_id": "143",
        "new_date": "2025-03-10",
        "time_window": "MORNING",
        "reason": "no estoy en casa",
    }

    handler.awaiting_confirmation = True

    r1 = handler.handle("no")

    assert handler.awaiting_edit_choice
    assert "corregir" in r1.lower()