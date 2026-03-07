from agent.llm import detect_intent
from agent.config import load_client_config, get_message, get_policy
from agent.status.handler import StatusHandler
from agent.tickets.handler import TicketHandler
from agent.reschedule.handler import RescheduleHandler

_RELEASE_CONTROL = "__RELEASE__"


class Agent:
    def __init__(self, client_name: str = None):
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
        user_message = user_message.strip()
        if not user_message:
            return self._msg("greeting")

        self.history.append({"role": "user", "content": user_message})
        response = self._process(user_message)
        self.history.append({"role": "assistant", "content": response})
        return response

    def reset(self) -> str:
        self.history        = []
        self.active_handler = None
        self.active_intent  = None
        self._unknown_count = 0
        return self._msg("greeting")

    def _process(self, user_message: str) -> str:
        if self.active_handler and not self.active_handler.is_done():
            response = self.active_handler.handle(user_message)

            if self.active_handler.is_done():
                self.active_handler = None
                self.active_intent  = None

                if response == _RELEASE_CONTROL:
                    return self._detect_and_route(user_message)

            return response

        return self._detect_and_route(user_message)

    def _detect_and_route(self, user_message: str) -> str:
        try:
            detection = detect_intent(user_message)
        except RuntimeError as e:
            return f"⚠️ {str(e)}"

        intent         = detection["intent"]
        prefilled_date = detection.get("new_date")
        prefilled_time = detection.get("time_window")

        # Guardia anti-alucinación: solo usar el ID si aparece literalmente en el mensaje
        raw_id = detection.get("shipment_id")
        prefilled_id = raw_id if (raw_id and raw_id in user_message) else None

        if intent == "GREETING":
            self._unknown_count = 0
            return self._msg("greeting")

        if intent == "CANCEL":
            self._unknown_count = 0
            if self.active_handler:
                self.active_handler = None
                self.active_intent  = None
            return self._msg("cancel_confirmation")

        if intent == "STATUS_QUERY":
            self._unknown_count = 0
            handler = StatusHandler(config=self.config)   # ← pasa config
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        elif intent == "CREATE_TICKET":
            self._unknown_count = 0
            handler = TicketHandler(config=self.config)   # ← pasa config
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        elif intent == "RESCHEDULE":
            self._unknown_count = 0
            handler = RescheduleHandler(config=self.config)
            # prefill valida cada valor antes de usarlo — descarta silenciosamente los inválidos
            handler.prefill(
                shipment_id=prefilled_id,
                new_date=prefilled_date,
                time_window=prefilled_time,
            )
            self.active_handler = handler
            self.active_intent  = intent
            return handler.handle(user_message)

        else:
            self._unknown_count += 1
            if self._unknown_count >= self._max_unknown:
                self._unknown_count = 0
                return self._msg("escalation")
            return self._msg("unknown_intent")

    def _msg(self, key: str, **kwargs) -> str:
        msg = get_message(self.config, key, name=self.config.get("name", "LogiBot"), **kwargs)
        if msg:
            return msg

        fallbacks = {
            "greeting": "¿En qué puedo ayudarle?",
            "cancel_confirmation": "Operación cancelada. ¿En qué más puedo ayudarle?",
            "unknown_intent": "No entendí su solicitud. ¿Puede reformularla?",
            "escalation": "Le conectaremos con un agente humano. 👋",
            "farewell": "¡Hasta pronto!",
        }
        return fallbacks.get(key, "¿En qué puedo ayudarle?")

    @staticmethod
    def _default_config() -> dict:
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