from agent.reschedule.tool_reschedule import (
    RESCHEDULE_SLOTS,
    get_next_missing_slot,
    fill_slot,
    do_reschedule,
)

from agent.config import get_message, get_policy

CANCEL_WORDS  = {"cancel", "cancelar", "stop", "salir", "abortar"}
CONFIRM_WORDS = {"si", "sí", "yes"}
DENY_WORDS    = {"no"}
MAX_RETRIES   = 3


class RescheduleHandler:
    """
    Handler para RESCHEDULE.
    Recibe el config del cliente para usar sus mensajes y políticas.
    
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
        self.awaiting_edit_choice  = False
        self.editing_slot          = None

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()
        msg = user_message.lower()

        if msg in CANCEL_WORDS:
            self.done = True
            return self._msg("reschedule_cancelled")

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

            self.current_slot = None

        return self._next_turn()

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

        self.awaiting_confirmation = True
        return self._confirm_reschedule()

    def _confirm_reschedule(self) -> str:
        return (
            "Voy a realizar la siguiente reprogramación:\n\n"
            f"Envío:   {self.collected.get('shipment_id')}\n"
            f"Fecha:   {self.collected.get('new_date')}\n"
            f"Horario: {self.collected.get('time_window')}\n"
            f"Motivo:  {self.collected.get('reason')}\n\n"
            "¿Confirma la reprogramación?\n"
            "Responda SI para confirmar o NO para modificar algún dato."
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
            "1. Fecha\n"
            "2. Horario\n"
            "3. Motivo\n\n"
            "Escriba el número o el nombre del campo."
        )

    def _handle_edit_choice(self, msg: str) -> str:
        mapping = {
            "1": "new_date", "fecha": "new_date",
            "2": "time_window","horario": "time_window",
            "3": "reason", "motivo": "reason", "razón": "reason", "razon": "reason",
        }

        slot_key = mapping.get(msg.strip())
        if not slot_key:
            return "Por favor elija una opción válida (1-3)."

        slot = next(s for s in RESCHEDULE_SLOTS if s["key"] == slot_key)
        self.awaiting_edit_choice = False
        self.editing_slot = slot_key
        self.current_slot = slot
        return f"Por favor ingrese el nuevo valor.\n\n{slot['question']}"

    def _handle_slot_edit(self, user_message: str) -> str:
        slot_key = self.editing_slot
        success, error = fill_slot(self.collected, slot_key, user_message)

        if not success:
            return f"{error}\n\n{self.current_slot['question']}"

        self.editing_slot = None
        self.current_slot = None
        self.awaiting_confirmation = True
        return self._confirm_reschedule()

    def _submit(self) -> str:
        response = do_reschedule(self.collected)
        self.done = True
        self.result = response

        if response.get("success"):
            updated = response.get("updated", {})
            # Usar mensaje del cliente si existe
            client_msg = self._msg(
                "reschedule_confirmation",
                id = self.collected.get("shipment_id", "N/A"),
                new_date = updated.get("new_date", self.collected.get("new_date", "N/A")),
                time_window = updated.get("time_window", self.collected.get("time_window", "N/A")),
            )
            if client_msg:
                return client_msg

            # Fallback detallado
            return (
                f"¡Reprogramación realizada con éxito!\n\n"
                f"Envío:   {self.collected.get('shipment_id', 'N/A')}\n"
                f"Fecha:   {updated.get('new_date', self.collected.get('new_date', 'N/A'))}\n"
                f"Horario: {updated.get('time_window', self.collected.get('time_window', 'N/A'))}\n\n"
                "¿Hay algo más en lo que pueda ayudarle?"
            )

        return (
            f"No se pudo realizar la reprogramación:\n{response.get('error', 'Error desconocido')}\n\n"
            "Por favor intente nuevamente o contacte a soporte."
        )

    def _msg(self, key: str, **kwargs) -> str:
        msg = get_message(self.config, key, **kwargs)
        if msg:
            return msg

        fallbacks = {
            "reschedule_cancelled": "Reprogramación cancelada. ¿En qué más puedo ayudarle?",
            "escalation": "No pude obtener la información necesaria. Le conectamos con un agente humano. 👋",
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