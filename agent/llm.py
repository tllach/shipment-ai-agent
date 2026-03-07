import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

INTENT_SYSTEM_PROMPT = """Eres un clasificador de intenciones para un sistema logístico de transporte y envíos.
Tu única tarea es analizar el mensaje del usuario y responder ÚNICAMENTE con un objeto JSON válido.
No agregues texto adicional, explicaciones ni markdown.

═══════════════════════════════════════════════
INTENCIONES DISPONIBLES
═══════════════════════════════════════════════

STATUS_QUERY
→ El usuario quiere saber dónde está un envío, su estado actual, ETA o historial.
→ Ejemplos: "¿dónde está mi paquete?", "estado del envío 123", "when will my order arrive?","quiero saber del envío", "track my shipment"

RESCHEDULE
→ El usuario quiere cambiar la fecha o el horario de una entrega o recolección.
→ Ejemplos: "quiero reprogramar", "cambiar fecha de entrega", "reschedule my delivery", "no puedo recibir el martes", "cambiar el horario"

CREATE_TICKET
→ El usuario quiere reportar un problema: daño, retraso, pérdida, entrega incorrecta, facturación.
→ Ejemplos: "mi paquete llegó roto", "el envío está tardando mucho", "package is damaged", "quiero reportar un problema", "necesito abrir un caso"

CANCEL
→ El usuario quiere cancelar la operación actual o salir.
→ Ejemplos: "cancelar", "olvídalo", "cancel", "quiero salir", "stop", "no importa"

GREETING
→ El usuario saluda o hace un comentario social sin intención logística.
→ Ejemplos: "hola", "buenas", "hello", "gracias", "thanks", "ok", "perfecto"

UNKNOWN
→ SOLO usar si el mensaje no encaja en ninguna de las categorías anteriores y no hay forma razonable de inferir una intención logística.
→ Ejemplos: "¿cuánto cuesta enviar?", "¿tienen sucursal en Bogotá?"

═══════════════════════════════════════════════
EXTRACCIÓN DE ENTIDADES
═══════════════════════════════════════════════

Extrae estas entidades si están presentes en el mensaje:

- shipment_id : ID alfanumérico del envío (ej: "14309635", "H624599IDL"). Si no hay ID claro, pon null.
- new_date    : Fecha mencionada en formato YYYY-MM-DD si es posible, si no, el texto tal cual. Ej: "el lunes" → "el lunes", "2025-04-15" → "2025-04-15". Si no hay, null.
- time_window : Horario o franja horaria mencionada. Ej: "en la mañana", "08:00-12:00". Si no hay, null.
- language    : Idioma del mensaje. "es" para español, "en" para inglés.

═══════════════════════════════════════════════
REGLAS ESTRICTAS
═══════════════════════════════════════════════

1. NUNCA inventes entidades que no estén explícitamente en el mensaje.
2. Si el mensaje es ambiguo entre STATUS_QUERY y RESCHEDULE, elige STATUS_QUERY.
3. Un número solo (ej: "14309635") clasifícalo como STATUS_QUERY con ese shipment_id.
4. Saludes y agradecimientos → siempre GREETING, nunca UNKNOWN.
5. Responde SOLO con el JSON, sin texto antes ni después.

═══════════════════════════════════════════════
FORMATO DE RESPUESTA
═══════════════════════════════════════════════

{
    "intent": "STATUS_QUERY",
    "shipment_id": "14309635",
    "new_date": null,
    "time_window": null,
    "language": "es",
    "confidence": "high"
}

Valores de confidence:
- "high"   → estás seguro de la intención
- "medium" → el mensaje es algo ambiguo
- "low"    → estás inferiendo, no es explícito
"""


# Response generation prompt
# Usado para generar respuestas en lenguaje natural con el tono del cliente

def build_response_prompt(client_config: dict) -> str:
    """
    Construye el system prompt para generación de respuestas
    según el tono y políticas del cliente.
    """
    tone    = client_config.get("tone", "formal")
    name    = client_config.get("name", "LogiBot")
    lang    = client_config.get("language", "es")
    policies = client_config.get("policies", {})

    no_hallucination      = policies.get("no_hallucination", True)
    escalate_after        = policies.get("escalate_after_attempts", 2)
    allow_language_switch = policies.get("allow_language_switch", True)

    tone_instructions = {
        "formal": (
            "Usa un lenguaje formal y profesional. "
            "Tratar al usuario de 'usted'. "
            "Evita emojis. Sé conciso y preciso."
        ),
        "casual": (
            "Usa un lenguaje cercano y amigable. "
            "Tratar al usuario de 'tú'. "
            "Puedes usar emojis con moderación baja. "
            "Sé cálido y empático."
        ),
    }

    hallucination_rule = (
        "\n- NUNCA inventes datos de envíos, fechas, estados ni tickets. "
        "Si no tienes el dato, dilo claramente."
        if no_hallucination else ""
    )

    language_rule = (
        f"\n- Si el usuario escribe en inglés, responde en inglés. "
        f"Si escribe en español, responde en español."
        if allow_language_switch
        else f"\n- Responde siempre en {'español' if lang == 'es' else 'inglés'}."
    )

    return f"""Eres LogiBot, el asistente virtual de soporte logístico de {name}.

TONO Y ESTILO:
{tone_instructions.get(tone, tone_instructions['formal'])}

REGLAS OBLIGATORIAS:{hallucination_rule}{language_rule}
- Solo puedes ayudar con: consultar estado de envíos, reprogramar entregas y crear tickets de soporte.
- Si el usuario pide algo fuera de tu alcance, explícalo amablemente y ofrece las opciones disponibles.
- Nunca confirmes una acción que no hayas ejecutado realmente.
- Si el usuario falla {escalate_after} veces seguidas, escala a un agente humano.
- Sé conciso. No repitas información innecesariamente.

Recuerda: eres la cara de {name}. Cada respuesta refleja la calidad del servicio."""


# Core LLM functions

def chat(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Envía mensajes a Ollama y retorna la respuesta como string.
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "No se pudo conectar a Ollama. "
            "Asegúrate de que esté corriendo con: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama tardó demasiado en responder. Intenta de nuevo.")
    except Exception as e:
        raise RuntimeError(f"Error inesperado con Ollama: {e}")


def detect_intent(user_message: str) -> dict:
    """
    Clasifica la intención del usuario y extrae entidades.

    Returns:
        {
            intent: str,
            shipment_id: str | None,
            new_date: str | None,
            time_window: str | None,
            language: str,
            confidence: str
        }
    """
    messages = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]

    raw = chat(messages, temperature=0.0)

    try:
        clean  = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        # Normalizar y garantizar todas las claves
        return {
            "intent":      result.get("intent", "UNKNOWN").upper(),
            "shipment_id": result.get("shipment_id"),
            "new_date":    result.get("new_date"),
            "time_window": result.get("time_window"),
            "language":    result.get("language", "es"),
            "confidence":  result.get("confidence", "low"),
        }
    except json.JSONDecodeError:
        return {
            "intent":      "UNKNOWN",
            "shipment_id": None,
            "new_date":    None,
            "time_window": None,
            "language":    "es",
            "confidence":  "low",
        }


def generate_response(client_config: dict, conversation_history: list[dict]) -> str:
    """
    Genera una respuesta en lenguaje natural con el tono del cliente.

    Args:
        client_config: dict cargado del YAML del cliente
        conversation_history: historial de mensajes [{"role": ..., "content": ...}]
    """
    system = build_response_prompt(client_config)
    messages = [{"role": "system", "content": system}] + conversation_history
    return chat(messages, temperature=0.3)