from agent.llm import detect_intent, generate_response
from agent.config import load_client_config, get_message, get_policy, get_tone
from agent.status.handler import StatusHandler
from agent.tickets.handler import TicketHandler
from agent.reschedule.handler import RescheduleHandler

_RELEASE_CONTROL = "__RELEASE__"

class Agent:
    """
    Orquestador principal del agente conversacional.

    Uso:
        # Con cliente específico
        agent = Agent(client_name="cliente_a")

        # Sin cliente (usa defaults formales)
        agent = Agent()

        response = agent.chat("¿Dónde está mi envío 14309635?")
    """

    def __init__(self, client_name: str = None):
        # Cargar config del cliente o usar defaults
        if client_name:
            try:
                self.config = load_client_config(client_name)
            except FileNotFoundError as e:
                print(f"[Agent] Advertencia: {e}. Usando configuración por defecto.")
                self.config = self._default_config()
        else:
            self.config = self._default_config()

        self.client_name    = client_name
        self.history        = []
        self.active_handler = None
        self.active_intent  = None
        self._unknown_count = 0
        self._max_unknown   = get_policy(self.config, "escalate_after_attempts", 2)


    def chat(self, user_message: str) -> str:
        """Punto de entrada único. Recibe mensaje del usuario, retorna respuesta."""
        user_message = user_message.strip()

        if not user_message:
            return self._msg("greeting")

        self.history.append({"role": "user", "content": user_message})
        response = self._process(user_message)
        self.history.append({"role": "assistant", "content": response})
        return response

    def reset(self) -> str:
        """Reinicia la sesión completa."""
        self.history        = []
        self.active_handler = None
        self.active_intent  = None
        self._unknown_count = 0
        return self._msg("greeting")

    # Core routing

    def _process(self, user_message: str) -> str:

        # Caso 1: handler activo → continuar conversación en curso
        if self.active_handler and not self.active_handler.is_done():
            response = self.active_handler.handle(user_message)

            if self.active_handler.is_done():
                self.active_handler = None
                self.active_intent  = None

                if response == _RELEASE_CONTROL:
                    return self._detect_and_route(user_message)

            return response

        # Caso 2: detectar nueva intención
        return self._detect_and_route(user_message)

    def _detect_and_route(self, user_message: str) -> str:
        try:
            detection = detect_intent(user_message)
        except RuntimeError as e:
            return f"⚠️ {str(e)}"

        intent       = detection["intent"]
        prefilled_id = detection.get("shipment_id")
        prefilled_date = detection.get("new_date")
        prefilled_time = detection.get("time_window")


        if intent == "GREETING":
            self._unknown_count = 0
            return self._msg("greeting")

        if intent == "CANCEL":
            self._unknown_count = 0
            # Si hay handler activo, cancelarlo
            if self.active_handler:
                self.active_handler = None
                self.active_intent  = None
            return self._msg("cancel_confirmation")


        if intent == "STATUS_QUERY":
            self._unknown_count = 0
            handler = StatusHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        elif intent == "CREATE_TICKET":
            self._unknown_count = 0
            handler = TicketHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        elif intent == "RESCHEDULE":
            self._unknown_count = 0
            handler = RescheduleHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            # Pre-llenar fecha y horario si el LLM los extrajo
            if prefilled_date:
                handler.collected["new_date"] = prefilled_date
            if prefilled_time:
                handler.collected["time_window"] = prefilled_time
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        # UNKOWN
        else:
            self._unknown_count += 1
            if self._unknown_count >= self._max_unknown:
                self._unknown_count = 0
                return self._msg("escalation")
            return self._msg("unknown_intent")

    # Helpers

    def _msg(self, key: str, **kwargs) -> str:
        """
        Obtiene un mensaje formateado del config del cliente.
        Si no existe la clave, usa el fallback hardcodeado.
        """
        msg = get_message(self.config, key, name=self.config.get("name", "LogiBot"), **kwargs)
        if msg:
            return msg
        # Fallbacks hardcodeados por si el YAML no tiene la clave
        fallbacks = {
            "greeting":            "¿En qué puedo ayudarle?",
            "cancel_confirmation": "Operación cancelada. ¿En qué más puedo ayudarle?",
            "unknown_intent":      "No entendí su solicitud. ¿Puede reformularla?",
            "escalation":          "Le conectaremos con un agente humano. 👋",
            "farewell":            "Ha sido un placer. ¡Hasta pronto!",
        }
        return fallbacks.get(key, "¿En qué puedo ayudarle?")

    @staticmethod
    def _default_config() -> dict:
        """Config por defecto cuando no se especifica cliente."""
        return {
            "tone": "formal",
            "language": "es",
            "name": "LogiBot",
            "policies": {
                "no_hallucination": True,
                "require_confirmation": True,
                "escalate_after_attempts": 2,
                "allow_language_switch": True,
            },
            "message_formats": {},
        }
