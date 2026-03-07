from agent.status.tool_status import (
    get_next_missing_slot,
    fill_slot,
    format_status_response,
)
from agent.tools import get_shipment_status
from agent.config import get_message, get_policy

NEGATIVE_RESPONSES = {
    "no", "nope", "nada", "gracias", "no gracias", "está bien", "no, gracias",
    "listo", "ok", "okay", "perfecto", "eso es todo", "bye", "adiós", "no creo"
}

# Señal interna para que el orquestador retome el control
_RELEASE_CONTROL = "__RELEASE__"


class StatusHandler:
    """
    Handler para STATUS_QUERY.
    Recibe el config del cliente para usar sus mensajes y políticas.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.collected = {}
        self.current_slot = None
        self.done = False
        self.result = None
        self.attempts = 0
        self.max_attempts = get_policy(self.config, "escalate_after_attempts", 3)
        self._waiting_followup = False

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        user_message = user_message.strip()

        if self._waiting_followup:
            return self._handle_followup(user_message)

        if self.current_slot:
            slot_key = self.current_slot["key"]
            ok, error = fill_slot(self.collected, slot_key, user_message)

            if not ok:
                self.attempts += 1
                if self.attempts >= self.max_attempts:
                    self.done = True
                    return self._msg("escalation")
                return f"{error}\n\n{self.current_slot['question']}"

            self.current_slot = None
            self.attempts = 0

        return self._next_turn()

    def _handle_followup(self, user_message: str) -> str:
        normalized = user_message.lower().strip(".,!¿?")

        if normalized in NEGATIVE_RESPONSES:
            self.done = True
            return self._msg("farewell")

        # Usuario quiere algo más → mostrar menú y marcar done
        # El agente principal retoma el control en el próximo turno
        self._waiting_followup = False
        self.done = True
        follow_up_menu = self._msg("follow_up_menu")
        if not follow_up_menu:
            follow_up_menu = (
                "¿En qué más puedo ayudarte?\n\n"
                "• Reprogramar este envío \n"
                "• Reportar un problema \n"
                "• Consultar otro envío \n"
            )
        return follow_up_menu

    def _next_turn(self) -> str:
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        return self._query()

    def _query(self) -> str:
        shipment_id = self.collected["shipment_id"]
        response = get_shipment_status(shipment_id)
        self.result = response

        if response["success"]:
            data = response["data"]
            status = data.get("status", "")
            origin = data.get("origin", {})
            dest = data.get("destination", {})
            cargo = data.get("cargo", {})
            container = data.get("container", "")

            # Calcular días relativos para la fecha de entrega
            from agent.status.tool_status import _days_until
            dest_date = dest.get("date", "")
            dest_time = dest.get("time", "")
            dest_relative = _days_until(dest_date) if dest_date else ""

            origin_date = origin.get("date", "")
            origin_time = origin.get("time", "")
            origin_relative = _days_until(origin_date) if origin_date else ""

            # Todas las variables disponibles para el template del cliente
            template_vars = dict(
                id = shipment_id,
                status = status,
                order_type = data.get("order_type", ""),
                container = container,
                # Origen
                origin = f"{origin.get('name', '')} — {origin.get('city', '')}, {origin.get('state', '')}",
                origin_name = origin.get("name", ""),
                origin_city = origin.get("city", ""),
                origin_state = origin.get("state", ""),
                origin_date = origin_date,
                origin_time = origin_time,
                origin_relative = origin_relative,
                # Destino
                destination = f"{dest.get('name', '')} — {dest.get('city', '')}, {dest.get('state', '')}",
                dest_name = dest.get("name", ""),
                dest_city = dest.get("city", ""),
                dest_state = dest.get("state", ""),
                dest_date = dest_date,
                dest_time = dest_time,
                dest_relative = dest_relative,
                # Carga
                weight = cargo.get("weight_lbs", ""),
                pieces = cargo.get("pieces", ""),
                bol = cargo.get("bol", ""),
                seal = cargo.get("seal", ""),
            )

            # Si el YAML tiene status_update → el cliente controla el mensaje completo
            # Si no → usar el formatter detallado por defecto
            client_msg = self._msg("status_update", **template_vars)
            formatted  = client_msg if client_msg else format_status_response(data)

            self._waiting_followup = True
            followup = self._msg("followup_question")
            if not followup:
                followup = "¿Necesitas algo más con este envío?"
            return formatted + f"\n\n{followup}"

        if response.get("not_found"):
            self.done = True
            return self._msg("status_not_found", id=self.collected.get("shipment_id", ""))

        self.done = True
        return f"⚠️ {response.get('error', 'Error desconocido')}"

    def _msg(self, key: str, **kwargs) -> str:
        """Obtiene mensaje del YAML del cliente con fallbacks hardcodeados."""
        msg = get_message(self.config, key, **kwargs)
        if msg:
            return msg

        fallbacks = {
            "farewell": "¡Con gusto! Si necesita algo más, no dude en escribirnos. 👋",
            "escalation": "No pude obtener el número de envío. Le conectamos con un agente humano. 👋",
            "status_not_found":"No encontré ningún envío con ese ID. Por favor verifica el número e intenta de nuevo.",
            "unknown_intent": (
                "¿En qué más puedo ayudarle?\n\n"
                "• Reprogramar este envío\n"
                "• Reportar un problema\n"
                "• Consultar otro envío"
            ),
        }
        return fallbacks.get(key, "")

    def summary(self) -> dict:
        return {
            "collected_slots": self.collected,
            "done": self.done,
            "result": self.result,
        }