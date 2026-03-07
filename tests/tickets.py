import pytest
from unittest.mock import patch

from agent.tickets.handler import TicketHandler


# Test 1: flujo completo exitoso

@patch("agent.tickets.handler.create_ticket")
@patch("agent.tickets.handler.get_tickets_for_shipment")
@patch("agent.tickets.handler.fill_slot")
@patch("agent.tickets.handler.get_next_missing_slot")
def test_ticket_creation_success(
    mock_next_slot,
    mock_fill_slot,
    mock_get_tickets,
    mock_create_ticket,
):

    handler = TicketHandler()

    # Simular slots
    mock_next_slot.side_effect = [
        {"key": "shipment_id", "question": "ID?"}, 
        {"key": "issue_type", "question": "Issue?"}, 
        {"key": "description", "question": "Description?"}, 
        {"key": "contact_email", "question": "Email?"}, 
        None
    ]

    mock_fill_slot.return_value = (True, "")

    mock_get_tickets.return_value = {
        "success": True,
        "data": []
    }

    mock_create_ticket.return_value = {
        "success": True,
        "data": {
            "ticket": {
                "ticket_id": "T123",
                "shipment_id": "143",
                "issue_type": "DAÑO",
                "status": "OPEN",
                "contact_email": "user@test.com"
            }
        }
    }

    # Conversación
    r1 = handler.handle("hola")
    r2 = handler.handle("143")
    r3 = handler.handle("daño")
    r4 = handler.handle("llego roto completamente")
    r5 = handler.handle("user@test.com")

    assert handler.awaiting_confirmation

    r6 = handler.handle("si")

    assert handler.is_done()
    assert "ticket ha sido creado" in r6.lower()


# Test 2: cancelación

def test_cancel_ticket():

    handler = TicketHandler()

    response = handler.handle("cancelar")

    assert handler.is_done()
    assert "cancelado" in response.lower()


# Test 3: edición de campo

def test_edit_flow():

    handler = TicketHandler()

    handler.collected = {
        "shipment_id": "143",
        "issue_type": "DAÑO",
        "description": "paquete roto",
        "contact_email": "user@test.com",
    }

    handler.awaiting_confirmation = True

    r1 = handler.handle("no")

    assert handler.awaiting_edit_choice
    assert "corregir" in r1.lower()

    r2 = handler.handle("2")

    assert handler.editing_slot == "description"


# Test 4: retry cuando slot falla

@patch("agent.tickets.handler.fill_slot")
def test_slot_retry(mock_fill_slot):

    handler = TicketHandler()

    handler.current_slot = {
        "key": "contact_email",
        "question": "Email?"
    }

    mock_fill_slot.return_value = (False, "Email inválido")

    r1 = handler.handle("bademail")

    assert "email inválido" in r1.lower()
    assert handler.attempts["contact_email"] == 1


# Test 5: ticket duplicado

@patch("agent.tickets.handler.get_tickets_for_shipment")
def test_duplicate_ticket(mock_get_tickets):

    handler = TicketHandler()

    handler.collected = {
        "shipment_id": "143",
        "issue_type": "DAÑO",
        "description": "paquete roto",
        "contact_email": "user@test.com",
    }

    mock_get_tickets.return_value = {
        "success": True,
        "data": [{"ticket_id": "T999"}]
    }

    response = handler._next_turn()

    assert handler.is_done()
    assert "ya existe un ticket" in response.lower()




