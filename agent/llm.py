import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

system_prompt = """Eres un clasificador de intenciones para un sistema logístico.
Analiza el mensaje del usuario y responde ÚNICAMENTE con un JSON válido, sin texto adicional.

Las intenciones posibles son:
- STATUS_QUERY: el usuario quiere saber el estado, ubicación o ETA de un envío
- RESCHEDULE: el usuario quiere reprogramar una entrega o recolección
- CREATE_TICKET: el usuario quiere reportar un problema (daño, retraso, pérdida, error de entrega, facturación)
- UNKNOWN: no encaja en ninguna de las anteriores.

Restricciones:
- Si el usuario menciona un ID de envío (números o alfanumérico), extraelo y colócalo en "shipment_id". Si no, pon null.
- Si no estás seguro de la intención, clasifícala como UNKNOWN.
- Si la intención es STATUS_QUERY pero no se menciona un ID de envío, pon shipment_id como null pero aún así clasifícalo como STATUS_QUERY.

Extrae también el shipment_id si el usuario lo menciona (solo números o alfanumérico), sino null.

Formato de respuesta (solo JSON):
{
    "intent": "STATUS_QUERY",
    "shipment_id": "14309635",
    "confidence": "high"
}"""


def chat(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Envía una conversación al modelo y retorna la respuesta como string.

    Args:
        messages: Lista de {"role": "system"|"user"|"assistant", "content": "..."}
        temperature: 0.0 = determinístico, 1.0 = creativo. Usamos 0.2 para consistencia.

    Returns:
        Texto de respuesta del modelo.
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()

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
    Usa el LLM para clasificar la intención del usuario.

    Returns dict con:
        - intent: "STATUS_QUERY" | "RESCHEDULE" | "CREATE_TICKET" | "UNKNOWN"
        - shipment_id: str | None  (si el usuario lo mencionó)
        - confidence: "high" | "low"
    """
    

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    raw = chat(messages, temperature=0.0)

    # Parsear JSON de la respuesta
    try:
        # Limpiar posibles backticks que el modelo agregue
        clean = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        # Normalizar
        result["intent"] = result.get("intent", "UNKNOWN").upper()
        result["shipment_id"] = result.get("shipment_id")
        result["confidence"] = result.get("confidence", "low")
        return result
    except json.JSONDecodeError:
        # Si el modelo no devolvió JSON limpio, fallback
        return {"intent": "UNKNOWN", "shipment_id": None, "confidence": "low"}


def generate_response(system_prompt: str, conversation_history: list[dict]) -> str:
    """
    Genera una respuesta en lenguaje natural dado un system prompt y el historial.
    Usado para formatear respuestas finales al usuario.
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    return chat(messages, temperature=0.3)