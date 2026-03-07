from agent.tickets.tool_tickets import (
    TICKET_SLOTS,
    get_next_missing_slot,
    fill_slot,
    create_ticket,
    get_tickets_for_shipment,
)
from agent.config import get_message, get_policy
from agent.tools import get_shipment_status

CANCEL_WORDS  = {"cancel", "cancelar", "stop", "salir", "abortar"}
CONFIRM_WORDS = {"si", "sí", "yes"}
DENY_WORDS    = {"no"}
MAX_RETRIES   = 3


class TicketHandler:
    """
    Validación del shipment_id en dos pasos (antes de pedir más datos):
        1. Verificar que el envío existe en el API
        2. Verificar que NO tiene ticket activo
    Si cualquiera falla → informar y terminar. No se piden más datos.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.collected = {}
        self.current_slot = None
        self.done = False
        self.result = None
        self.attempts = {}
        self.max_retries = get_policy(self.config, "escalate_after_attempts", MAX_RETRIES)

        self.awaiting_confirmation = False
        self.awaiting_edit_choice = False
        self.editing_slot = None

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()
        msg = user_message.lower()

        if msg in CANCEL_WORDS:
            self.done = True
            return self._msg("cancel_confirmation")

        if self.awaiting_confirmation:
            return self._handle_confirmation(msg)

        if self.awaiting_edit_choice:
            return self._handle_edit_choice(msg)

        if self.editing_slot:
            return self._handle_slot_edit(user_message)

        # Normal slot filling
        if self.current_slot:
            slot_key = self.current_slot["key"]
            success, error = fill_slot(self.collected, slot_key, user_message)

            if not success:
                return self._handle_retry(slot_key, error)
            
            # Validación temprana del shipment_id, antes de pedir más datos
            if slot_key == "shipment_id":
                early_check = self._validate_shipment_id(user_message.strip())
                if early_check:
                    return early_check
            
            if slot_key == "description" and len(user_message) < 15:
                return self._handle_retry(
                    slot_key,
                    "Por favor proporciona una descripción más detallada del problema.",
                )

            self.current_slot = None

        return self._next_turn()
    
    
    def _validate_shipment_id(self, shipment_id: str) -> str | None:
        """
        Valida el shipment_id en dos pasos:
            1. ¿Existe el envío?
            2. ¿Ya tiene un ticket activo?
        Retorna mensaje de error si falla, None si todo está bien.
        """
        
        #  verificar que el envío existe
        status_resp = get_shipment_status(shipment_id)
        if not status_resp.get("success"):
            self.done = True
            if status_resp.get("not_found"):
                return self._msg(
                    "status_not_found",
                    id=shipment_id
                ) or f"No encontré ningún envío con el ID '{shipment_id}'. Por favor verifica el número."
            return f"⚠️ {status_resp.get('error', 'Error al consultar el envío.')}"

        # verificar que no tiene ticket activo
        ticket_resp = get_tickets_for_shipment(shipment_id)
        if ticket_resp.get("success") and ticket_resp.get("data"):
            self.done = True
            return self._msg("ticket_exists", id=shipment_id)

        return None

    def _handle_retry(self, slot_key: str, error: str) -> str:
        self.attempts[slot_key] = self.attempts.get(slot_key, 0) + 1

        if self.attempts[slot_key] >= self.max_retries:
            if self.current_slot and self.current_slot.get("required"):
                self.done = True
                return self._msg("escalation")
            
            self.collected[slot_key] = None
            self.current_slot = None
            return self._next_turn()

        return f"{error}\n\n{self.current_slot['question']}"

    def _next_turn(self) -> str:
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        # Verificar si ya existe ticket para este envío
        shipment_id = self.collected.get("shipment_id")
        if shipment_id:
            existing = get_tickets_for_shipment(shipment_id)
            if existing["success"] and existing["data"]:
                self.done = True
                return self._msg("ticket_exists", id=shipment_id)

        self.awaiting_confirmation = True
        return self._confirm_ticket()

    def _confirm_ticket(self) -> str:
        return (
            "Voy a crear el siguiente ticket:\n\n"
            f"Envío:       {self.collected.get('shipment_id')}\n"
            f"Problema:    {self.collected.get('issue_type')}\n"
            f"Descripción: {self.collected.get('description')}\n"
            f"Email:       {self.collected.get('contact_email')}\n\n"
            "¿Confirma que desea crear este ticket?\n"
            "Responda SI para confirmar o NO para modificar."
        )

    def _handle_confirmation(self, msg: str) -> str:
        if msg in CONFIRM_WORDS:
            return self._submit()
        if msg in DENY_WORDS:
            self.awaiting_confirmation = False
            self.awaiting_edit_choice  = True
            return self._ask_what_to_edit()
        return "Por favor responda SI para confirmar o NO para cambiar algún dato."

    def _ask_what_to_edit(self) -> str:
        return (
            "¿Qué dato desea corregir?\n\n"
            "1. Tipo de problema (DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS)\n"
            "2. Descripción\n"
            "3. Correo electrónico\n\n"
            "Escriba el número o el nombre del campo."
        )

    def _handle_edit_choice(self, msg: str) -> str:
        mapping = {
            "1": "issue_type", "problema": "issue_type",
            "el tipo de problema": "issue_type", "el problema": "issue_type",
            "2": "description", "descripcion": "description", "descripción": "description",
            "3": "contact_email", "correo": "contact_email",
            "correo electronico": "contact_email", "correo electrónico": "contact_email",
        }

        slot_key = mapping.get(msg.strip())
        if not slot_key:
            return "Por favor elija una opción válida (1-3)."

        slot = next(s for s in TICKET_SLOTS if s["key"] == slot_key)
        self.awaiting_edit_choice = False
        self.editing_slot  = slot_key
        self.current_slot  = slot
        return f"Por favor ingrese el nuevo valor.\n\n{slot['question']}"

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
        self.done   = True
        self.result = response

        if response.get("success"):
            ticket = response["data"]["ticket"]
            # Usar mensaje del cliente si existe
            client_msg = self._msg(
                "ticket_creation",
                ticket_id=ticket["ticket_id"],
                contact_email=ticket.get("contact_email", ""),
                id=ticket["shipment_id"],
            )
            if client_msg:
                return client_msg

            # Fallback detallado
            return (
                f"Su ticket ha sido creado correctamente.\n\n"
                f"Ticket ID: {ticket['ticket_id']}\n"
                f"Envío:     {ticket['shipment_id']}\n"
                f"Problema:  {ticket['issue_type']}\n"
                f"Estado:    {ticket['status']}\n\n"
                f"Nuestro equipo se pondrá en contacto con usted en {ticket.get('contact_email', 'breve')}."
            )

        return (
            f"Ocurrió un problema al crear el ticket:\n{response.get('error', 'Error desconocido')}\n\n"
            "Por favor intente nuevamente más tarde."
        )

    def _msg(self, key: str, **kwargs) -> str:
        msg = get_message(self.config, key, **kwargs)
        if msg:
            return msg

        fallbacks = {
            "cancel_confirmation": "Creación de ticket cancelada. ¿En qué más puedo ayudarle?",
            "escalation": "No pude obtener la información necesaria. Le conectamos con un agente humano. 👋",
            "ticket_exists": "Ya existe un ticket activo para este envío. Nuestro equipo ya está atendiendo su caso.",
        }
        return fallbacks.get(key, "")

    def summary(self) -> dict:
        return {
            "collected_slots": self.collected,
            "attempts": self.attempts,
            "awaiting_confirmation": self.awaiting_confirmation,
            "editing_slot": self.editing_slot,
            "done": self.done,
            "result": self.result,
        }