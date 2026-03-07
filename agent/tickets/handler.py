from agent.tickets.tool_tickets import (
    get_next_missing_slot,
    fill_slot,
    create_ticket,
    get_tickets_for_shipment,
)

CANCEL_WORDS = {"cancel", "cancelar", "stop", "salir", "abortar"}
CONFIRM_WORDS = {"si", "sí", "yes", "confirmar"}
DENY_WORDS = {"no", "cancelar", "negativo", "incorrecto", "ya no"}

MAX_RETRIES = 3


class TicketHandler:
    """
    Conversational handler for ticket creation.

    Features:
    - Slot filling
    - Validation
    - Retry logic
    - Ticket confirmation
    - Duplicate ticket detection
    - Cancel support
    """

    def __init__(self):
        self.collected: dict = {}
        self.current_slot: dict | None = None
        self.done: bool = False
        self.result: dict | None = None
        self.attempts: dict = {}
        self.awaiting_confirmation: bool = False

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()

        # Cancel command
        if user_message.lower() in CANCEL_WORDS:
            self.done = True
            return "He cancelado la creación del ticket. ¿Hay algo más en lo que pueda ayudarte?"

        # Confirmation stage
        if self.awaiting_confirmation:
            return self._handle_confirmation(user_message)

        # If waiting for a slot value
        if self.current_slot:
            slot_key = self.current_slot["key"]

            # Optional slot skipping
            if (
                user_message.lower() in ("skip", "no", "none", "-", "n/a")
                and not self.current_slot.get("required")
            ):
                self.collected[slot_key] = None
                self.current_slot = None
                return self._next_turn()

            success, error = fill_slot(self.collected, slot_key, user_message)

            if not success:
                return self._handle_retry(slot_key, error)

            # Extra validation for description length
            if slot_key == "description" and len(user_message) < 10:
                return self._handle_retry(
                    slot_key,
                    "Por favor proporciona una descripción un poco más detallada del problema.",
                )

            self.current_slot = None

        return self._next_turn()

    def _handle_retry(self, slot_key: str, error: str) -> str:
        """Retry logic for slot validation failures."""

        self.attempts[slot_key] = self.attempts.get(slot_key, 0) + 1

        if self.attempts[slot_key] >= MAX_RETRIES:
            if self.current_slot.get("required"):
                self.done = True
                return (
                    "No pude obtener la información necesaria después de varios intentos.\n"
                    "Voy a escalar este caso a un agente humano para que pueda ayudarte mejor."
                )

            self.collected[slot_key] = None
            self.current_slot = None
            return self._next_turn()

        return f"{error}\n\n{self.current_slot['question']}"

    def _next_turn(self) -> str:
        """Determine next step in conversation."""

        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        # All slots collected → check duplicates
        shipment_id = self.collected.get("shipment_id")

        if shipment_id:
            existing = get_tickets_for_shipment(shipment_id)

            if existing["success"] and existing["data"]:
                self.done = True
                return (
                    "Ya existe un ticket asociado a este envío.\n"
                    "Nuestro equipo ya está revisando el caso."
                )

        # Move to confirmation
        self.awaiting_confirmation = True
        return self._confirm_ticket()

    def _confirm_ticket(self) -> str:
        """Show ticket summary before submission."""

        summary = (
            "Voy a crear el siguiente ticket:\n\n"
            f"Envío: {self.collected.get('shipment_id')}\n"
            f"Problema: {self.collected.get('issue_type')}\n"
            f"Descripción: {self.collected.get('description')}\n"
            f"Email: {self.collected.get('contact_email')}\n\n"
            "¿Confirmas que deseas crear este ticket? (SI / NO)"
        )

        return summary

    def _handle_confirmation(self, user_message: str) -> str:
        """Handle user confirmation before ticket creation."""

        msg = user_message.lower()

        if msg in CONFIRM_WORDS:
            return self._submit()

        if msg in DENY_WORDS:
            self.done = True
            return "Entendido. He cancelado la creación del ticket."

        return "Por favor responde 'SI' para confirmar o 'NO' para cancelar."

    def _submit(self) -> str:
        """Call ticket API."""

        response = create_ticket(self.collected)

        self.done = True
        self.result = response

        if response["success"]:
            ticket = response["data"]["ticket"]

            return (
                "Tu ticket ha sido creado correctamente.\n\n"
                f"Ticket ID: {ticket['ticket_id']}\n"
                f"Envío: {ticket['shipment_id']}\n"
                f"Problema: {ticket['issue_type']}\n"
                f"Estado: {ticket['status']}\n\n"
                "Nuestro equipo revisará tu caso y se pondrá en contacto contigo "
                f"en {ticket.get('contact_email', 'breve')}."
            )

        return (
            f"Ocurrió un problema al crear el ticket:\n{response['error']}\n\n"
            "Por favor intenta nuevamente más tarde o contacta soporte."
        )

    def summary(self) -> dict:
        """Debug summary."""

        return {
            "collected_slots": self.collected,
            "attempts": self.attempts,
            "awaiting_confirmation": self.awaiting_confirmation,
            "done": self.done,
            "result": self.result,
        }