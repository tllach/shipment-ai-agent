from agent.status.tool_status import (
    get_next_missing_slot,
    fill_slot,
    get_shipment_status,
    format_status_response,
)

# Respuestas que indican que el usuario no necesita más ayuda
NEGATIVE_RESPONSES = {"no", "nope", "nada", "gracias", "no gracias", "está bien", "no, gracias",
                      "listo", "ok", "okay", "perfecto", "eso es todo", "bye", "adiós", "no creo"}

FAREWELL_MESSAGE = "¡Con gusto! Si necesitas algo más, no dudes en escribirme. 👋"

FOLLOW_UP_MESSAGE = "\n¿Necesitas hacer algo más con este envío?"

# Señal interna para que el orquestador retome el control
_RELEASE_CONTROL = "__RELEASE__"

class StatusHandler:
    """
    Handler para la intención STATUS_QUERY.

    Flujo:
        1. Si falta shipment_id → preguntarlo
        2. Consultar GET /shipments/{id}
        3. Formatear y retornar respuesta + pregunta de seguimiento
        4. Si el usuario dice "no" → despedirse y marcar done
        5. Si el usuario dice "sí" → el agente principal retoma el control
    """

    def __init__(self, max_attempts: int = 3):
        self.collected: dict   = {}
        self.current_slot      = None
        self.done: bool        = False
        self.result: dict      = None
        self.attempts: int     = 0
        self.max_attempts: int = max_attempts
        self._waiting_followup = False 

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        """Procesa un turno del usuario. Retorna la respuesta del agente."""
        user_message = user_message.strip()

        #  Caso: ya consultamos, esperamos si necesita algo más
        if self._waiting_followup:
            return self._handle_followup(user_message)

        # Caso: procesar respuesta al slot actual
        if self.current_slot:
            slot_key = self.current_slot["key"]
            ok, error = fill_slot(self.collected, slot_key, user_message)

            if not ok:
                self.attempts += 1
                if self.attempts >= self.max_attempts:
                    self.done = True
                    return (
                        "No pude obtener el número de envío después de varios intentos. "
                        "Te conecto con un agente humano. 👋"
                    )
                return f"{error}\n\n{self.current_slot['question']}"

            self.current_slot = None
            self.attempts = 0

        return self._next_turn()

    def _handle_followup(self, user_message: str) -> str:
        """Maneja la respuesta del usuario al '¿Necesitas algo más?'"""
        normalized = user_message.lower().strip(".,!¿?")

        if normalized in NEGATIVE_RESPONSES:
            self.done = True
            return FAREWELL_MESSAGE
        else:
            # El usuario quiere algo más → preguntarle qué necesita
            # para que el LLM tenga contexto suficiente para clasificar
            self._waiting_followup = False
            self.done = True
            return (
                "¿En qué más puedo ayudarte?\n\n"
                "• 📅 Reprogramar este envío\n"
                "• 🎫 Reportar un problema\n"
                "• 📦 Consultar otro envío"
            )

    def _next_turn(self) -> str:
        """Decide si pedir más datos o ejecutar la consulta."""
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        return self._query()

    def _query(self) -> str:
        """Llama al API y formatea la respuesta."""
        shipment_id = self.collected["shipment_id"]
        response = get_shipment_status(shipment_id)
        self.result = response

        if response["success"]:
            self._waiting_followup = True
            return format_status_response(response["data"]) + FOLLOW_UP_MESSAGE

        # Envío no encontrado
        if response.get("not_found"):
            self.done = True
            return (
                f"{response['error']}\n\n"
                "Por favor verifica el número e intenta de nuevo."
            )

        # Error de sistema
        self.done = True
        return f"{response['error']}"

    def summary(self) -> dict:
        return {
            "collected_slots": self.collected,
            "done": self.done,
            "result": self.result,
        }