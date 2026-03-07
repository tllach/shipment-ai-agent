from agent.reschedule.tool_reschedule import (
    RESCHEDULE_SLOTS,
    get_next_missing_slot,
    fill_slot,
    do_reschedule,
)

CANCEL_WORDS  = {"cancel", "cancelar", "stop", "salir", "abortar"}
CONFIRM_WORDS = {"si", "sí", "yes"}
DENY_WORDS    = {"no"}

MAX_RETRIES = 3


class RescheduleHandler:
    """
    Handler para la intención RESCHEDULE.

    Flujo (igual que TicketHandler):
        1. Recolectar slots: shipment_id, new_date, time_window, reason
        2. Mostrar resumen y pedir confirmación
        3. Si confirma → llamar al API
        4. Si niega → preguntar qué quiere editar
        5. En cualquier momento → cancelar con palabra clave
    """

    def __init__(self):
        self.collected: dict        = {}
        self.current_slot           = None
        self.done: bool             = False
        self.result: dict           = None
        self.attempts: dict         = {}

        self.awaiting_confirmation: bool = False
        self.awaiting_edit_choice:  bool = False
        self.editing_slot: str      = None

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()
        msg = user_message.lower()

        # Cancelar en cualquier momento
        if msg in CANCEL_WORDS:
            self.done = True
            return "He cancelado la reprogramación. ¿Hay algo más en lo que pueda ayudarte?"

        # Etapa de confirmación
        if self.awaiting_confirmation:
            return self._handle_confirmation(msg)

        # Etapa de edición — eligiendo qué campo cambiar
        if self.awaiting_edit_choice:
            return self._handle_edit_choice(msg)

        # Etapa de edición — ingresando el nuevo valor
        if self.editing_slot:
            return self._handle_slot_edit(user_message)

        # Llenado normal de slots
        if self.current_slot:
            slot_key = self.current_slot["key"]
            success, error = fill_slot(self.collected, slot_key, user_message)

            if not success:
                return self._handle_retry(slot_key, error)

            self.current_slot = None

        return self._next_turn()


    def _handle_retry(self, slot_key: str, error: str) -> str:
        self.attempts[slot_key] = self.attempts.get(slot_key, 0) + 1

        if self.attempts[slot_key] >= MAX_RETRIES:
            if self.current_slot and self.current_slot.get("required"):
                self.done = True
                return (
                    "No pude obtener la información necesaria después de varios intentos.\n"
                    "Voy a escalar este caso a un agente humano. 👋"
                )
            self.collected[slot_key] = None
            self.current_slot = None
            return self._next_turn()

        return f"{error}\n\n{self.current_slot['question']}"

    # Slot flow

    def _next_turn(self) -> str:
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        # Todos los slots listos → pedir confirmación
        self.awaiting_confirmation = True
        return self._confirm_reschedule()

    
    def _confirm_reschedule(self) -> str:
        return (
            "Voy a realizar la siguiente reprogramación:\n\n"
            f"Envío:    {self.collected.get('shipment_id')}\n"
            f"Fecha:    {self.collected.get('new_date')}\n"
            f"Horario:  {self.collected.get('time_window')}\n"
            f"Motivo:   {self.collected.get('reason')}\n\n"
            "¿Confirmas la reprogramación?\n"
            "Responde SI para confirmar o NO para modificar algún dato."
        )

    def _handle_confirmation(self, msg: str) -> str:
        if msg in CONFIRM_WORDS:
            return self._submit()

        if msg in DENY_WORDS:
            self.awaiting_confirmation = False
            self.awaiting_edit_choice  = True
            return self._ask_what_to_edit()

        return "Por favor responde SI para confirmar o NO para cambiar algún dato."

    # Edit flow

    def _ask_what_to_edit(self) -> str:
        return (
            "¿Qué dato deseas corregir?\n\n"
            "1. Fecha\n"
            "2. Horario\n"
            "3. Motivo\n\n"
            "Escribe el número o el nombre del campo."
        )

    def _handle_edit_choice(self, msg: str) -> str:
        mapping = {
            "1": "new_date",
            "2": "time_window",
            "3": "reason",
            "fecha": "new_date",
            "horario": "time_window",
            "motivo": "reason",
            "razón": "reason",
            "razon": "reason",
        }

        slot_key = mapping.get(msg.strip())

        if not slot_key:
            return "Por favor elige una opción válida (1-3)."

        slot = next(s for s in RESCHEDULE_SLOTS if s["key"] == slot_key)

        self.awaiting_edit_choice = False
        self.editing_slot  = slot_key
        self.current_slot  = slot

        return f"Por favor ingresa el nuevo valor para '{slot_key}'.\n\n{slot['question']}"

    def _handle_slot_edit(self, user_message: str) -> str:
        slot_key = self.editing_slot
        success, error = fill_slot(self.collected, slot_key, user_message)

        if not success:
            return f"{error}\n\n{self.current_slot['question']}"

        self.editing_slot         = None
        self.current_slot         = None
        self.awaiting_confirmation = True

        return self._confirm_reschedule()

    # Submit

    def _submit(self) -> str:
        response = do_reschedule(self.collected)
        self.done   = True
        self.result = response

        if response.get("success"):
            updated = response.get("updated", {})
            return (
                "¡Reprogramación realizada con éxito!\n\n"
                f"Envío:   {self.collected.get('shipment_id', 'N/A')}\n"
                f"Fecha:   {updated.get('new_date', self.collected.get('new_date', 'N/A'))}\n"
                f"Horario: {updated.get('time_window', self.collected.get('time_window', 'N/A'))}\n\n"
                "¿Hay algo más en lo que pueda ayudarte?"
            )

        return (
            f"No se pudo realizar la reprogramación:\n{response.get('error', 'Error desconocido')}\n\n"
            "Por favor intenta nuevamente o contacta a soporte."
        )

    # Debug

    def summary(self) -> dict:
        return {
            "collected_slots":      self.collected,
            "attempts":             self.attempts,
            "awaiting_confirmation": self.awaiting_confirmation,
            "editing_slot":         self.editing_slot,
            "done":                 self.done,
            "result":               self.result,
        }