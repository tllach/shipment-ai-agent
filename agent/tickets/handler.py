from agent.tickets.tool_tickets import (
    TICKET_SLOTS,
    get_next_missing_slot,
    fill_slot,
    create_ticket,
    get_tickets_for_shipment,
)

CANCEL_WORDS = {"cancel", "cancelar", "stop", "salir", "abortar"}
CONFIRM_WORDS = {"si", "sí", "yes"}
DENY_WORDS = {"no"}

MAX_RETRIES = 3

class TicketHandler:
    """
    Conversational handler for ticket creation.
    El proceso es el siguiente:
    1. El handler va pidiendo los datos necesarios (shipment_id, issue_type, description, contact_email) uno por uno.
    2. Si el usuario no responde adecuadamente, se le da un mensaje de error y se vuelve a pedir el mismo dato, hasta un máximo de intentos.
    3. Una vez se tienen todos los datos, se muestra un resumen y se pide confirmación.
    4. Si el usuario confirma, se llama a la API para crear el ticket y se muestra el resultado.
    5. Si el usuario quiere modificar algún dato, se le pregunta cuál y se le permite editarlo antes de volver a pedir confirmación.
    6. En cualquier momento, el usuario puede cancelar el proceso escribiendo una palabra de cancelación.
    """

    def __init__(self):
        self.collected: dict = {}
        self.current_slot: dict | None = None
        self.done: bool = False
        self.result: dict | None = None
        self.attempts: dict = {}

        self.awaiting_confirmation: bool = False
        self.awaiting_edit_choice: bool = False
        self.editing_slot: str | None = None

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()
        msg = user_message.lower()

        # Cancel anytime
        if msg in CANCEL_WORDS:
            self.done = True
            return "He cancelado la creación del ticket. ¿Hay algo más en lo que pueda ayudarte?"

        # Confirmation stage
        if self.awaiting_confirmation:
            return self._handle_confirmation(msg)

        # Editing stage
        if self.awaiting_edit_choice:
            return self._handle_edit_choice(msg)

        # If editing a specific slot
        if self.editing_slot:
            return self._handle_slot_edit(user_message)

        # Normal slot filling
        if self.current_slot:
            slot_key = self.current_slot["key"]

            success, error = fill_slot(self.collected, slot_key, user_message)

            if not success:
                return self._handle_retry(slot_key, error)

            if slot_key == "description" and len(user_message) < 15:
                return self._handle_retry(
                    slot_key,
                    "Por favor proporciona una descripción más detallada del problema.",
                )

            self.current_slot = None

        return self._next_turn()

    def _handle_retry(self, slot_key: str, error: str) -> str:
        self.attempts[slot_key] = self.attempts.get(slot_key, 0) + 1

        if self.attempts[slot_key] >= MAX_RETRIES:
            if self.current_slot.get("required"):
                self.done = True
                return (
                    "No pude obtener la información necesaria después de varios intentos.\n"
                    "Voy a escalar este caso a un agente humano."
                )

            self.collected[slot_key] = None
            self.current_slot = None
            return self._next_turn()

        return f"{error}\n\n{self.current_slot['question']}"

    def _next_turn(self) -> str:
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        shipment_id = self.collected.get("shipment_id")

        if shipment_id:
            existing = get_tickets_for_shipment(shipment_id)

            if existing["success"] and existing["data"]:
                self.done = True
                return (
                    "Ya existe un ticket asociado a este envío.\n"
                    "Nuestro equipo ya está revisando el caso."
                )

        self.awaiting_confirmation = True
        return self._confirm_ticket()

    def _confirm_ticket(self) -> str:
        return (
            "Voy a crear el siguiente ticket:\n\n"
            f"Envío: {self.collected.get('shipment_id')}\n"
            f"Problema: {self.collected.get('issue_type')}\n"
            f"Descripción: {self.collected.get('description')}\n"
            f"Email: {self.collected.get('contact_email')}\n\n"
            "¿Confirmas que deseas crear este ticket?\n"
            "Responde SI para confirmar o NO para modificar."
        )

    def _handle_confirmation(self, msg: str) -> str:

        if msg in CONFIRM_WORDS:
            return self._submit()

        if msg in DENY_WORDS:
            self.awaiting_confirmation = False
            self.awaiting_edit_choice = True
            return self._ask_what_to_edit()

        return "Por favor responde SI para confirmar o NO para cambiar algún dato."

    def _ask_what_to_edit(self) -> str:
        return (
            "¿Qué dato deseas corregir?\n\n"
            "1. El tipo de problema (DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS) \n"
            "2. Descripción\n"
            "3. Correo electronico\n\n"
            "Escribe el número o el nombre del campo."
        )

    def _handle_edit_choice(self, msg: str) -> str:

        mapping = {
            "1": "issue_type",
            "2": "description",
            "3": "contact_email",
            "problema": "issue_type",
            "el tipo de problema": "issue_type",
            "el problema": "issue_type",
            "descripcion": "description",
            "descripción": "description",
            "Correo electronico": "contact_email",
            "correo": "contact_email",
            "correo electronico": "contact_email",
        }

        slot_key = mapping.get(msg)

        if not slot_key:
            return "Por favor elige una opción válida (1-4)."

        slot = next(s for s in TICKET_SLOTS if s["key"] == slot_key)

        self.awaiting_edit_choice = False
        self.editing_slot = slot_key
        self.current_slot = slot

        return f"Por favor ingresa el nuevo valor para {slot_key}."

    def _handle_slot_edit(self, user_message: str) -> str:

        slot_key = self.editing_slot

        success, error = fill_slot(self.collected, slot_key, user_message)

        if not success:
            return error

        self.editing_slot = None
        self.current_slot = None
        self.awaiting_confirmation = True

        return self._confirm_ticket()

    def _submit(self) -> str:

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
            "Por favor intenta nuevamente más tarde."
        )

    def summary(self) -> dict:
        return {
            "collected_slots": self.collected,
            "attempts": self.attempts,
            "awaiting_confirmation": self.awaiting_confirmation,
            "editing_slot": self.editing_slot,
            "done": self.done,
            "result": self.result,
        }