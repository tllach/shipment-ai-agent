from agent.llm import detect_intent
from agent.status.handler import StatusHandler
from agent.tickets.handler import TicketHandler
from agent.reschedule.handler import RescheduleHandler


# Señal interna — el handler soltó el control, el orquestador debe retomar
_RELEASE_CONTROL = "__RELEASE__"


# Mensajes base

FALLBACK_MESSAGE = """Lo siento, no pude entender tu solicitud.

Puedo ayudarte con:
• 📦 Consultar el estado de un envío
• 📅 Reprogramar una entrega o recolección
• 🎫 Crear un ticket para reportar un problema

¿Con cuál de estas opciones puedo ayudarte?"""

UNKNOWN_INTENT_MESSAGE = """No estoy seguro de cómo ayudarte con eso.

Mis capacidades actuales son:
• 📦 Consultar estado de envíos → *"¿Dónde está mi envío 14309635?"*
• 📅 Reprogramar entregas → *"Necesito cambiar la fecha de entrega"*
• 🎫 Reportar un problema → *"Mi paquete llegó dañado"*

¿Puedes reformular tu consulta?"""


class Agent:
    """
    Orquestador principal del agente conversacional.

    Mantiene el estado de la sesión:
    - Historial de mensajes
    - Handler activo (si hay una conversación en curso)
    - Conteo de intentos desconocidos
    """

    def __init__(self, client_config: dict = None):
        self.client_config = client_config or {}
        self.history: list[dict] = []
        self.active_handler = None
        self.active_intent: str = None
        self.max_unknown_attempts: int = 2
        self._unknown_count: int = 0

    def chat(self, user_message: str) -> str:
        """
        Procesa un mensaje del usuario y retorna la respuesta del agente.
        Único método que necesita llamar la UI.
        """
        user_message = user_message.strip()
        if not user_message:
            return FALLBACK_MESSAGE

        self.history.append({"role": "user", "content": user_message})
        response = self._process(user_message)
        self.history.append({"role": "assistant", "content": response})
        return response

    def _process(self, user_message: str) -> str:
        """Lógica central de routing."""

        # Caso 1: handler activo → continuar conversación en curso
        if self.active_handler and not self.active_handler.is_done():
            response = self.active_handler.handle(user_message)

            if self.active_handler.is_done():
                self.active_handler = None
                self.active_intent = None
                
                # El handler soltó el control → el usuario quiere algo más
                if response == _RELEASE_CONTROL:
                    return self._detect_and_route(user_message)

            return response

        # Caso 2: detectar nueva intención con LLM
        return self._detect_and_route(user_message)


    def _detect_and_route(self, user_message: str) -> str:
        """Llama al LLM para detectar intención y delega al handler correcto."""
        try:
            detection = detect_intent(user_message)
        except RuntimeError as e:
            return f"{str(e)}"

        intent = detection["intent"]
        prefilled_id = detection.get("shipment_id")

        if intent == "STATUS_QUERY":
            self._unknown_count = 0
            handler = StatusHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent = intent
            return handler.handle(user_message)

        elif intent == "CREATE_TICKET":
            self._unknown_count = 0
            handler = TicketHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent = intent
            return handler.handle(user_message)

        elif intent == "RESCHEDULE":
            self._unknown_count = 0
            handler = RescheduleHandler()
            if prefilled_id:
                handler.collected["shipment_id"] = prefilled_id
            self.active_handler = handler
            self.active_intent = intent
            return handler.handle(user_message)

        else:
            self._unknown_count += 1
            if self._unknown_count >= self.max_unknown_attempts:
                self._unknown_count = 0
                return (
                    "Parece que no puedo entender tu solicitud. "
                    "Te voy a conectar con un agente humano que podrá ayudarte mejor. 👋"
                )
            return UNKNOWN_INTENT_MESSAGE
        
        
    def reset(self):
        """Reinicia la sesión completa."""
        self.history = []
        self.active_handler = None
        self.active_intent = None
        self._unknown_count = 0
        return "He reiniciado nuestra conversación. ¿En qué puedo ayudarte ahora?"

