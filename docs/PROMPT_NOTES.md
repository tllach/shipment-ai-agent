# PROMPT_NOTES — Ingeniería de Prompts

**Versión:** 1.0  
**Fecha:** 2026-03-07  
**Propósito:** Documentar las decisiones de diseño, iteraciones y aprendizajes del sistema de prompts del agente.

---

## Tabla de contenidos

- [Arquitectura de prompts](#arquitectura-de-prompts)
- [Prompt de detección de intenciones](#prompt-de-detección-de-intenciones)
- [Prompt de respuesta al usuario](#prompt-de-respuesta-al-usuario)
- [Iteraciones y problemas resueltos](#iteraciones-y-problemas-resueltos)
- [Reglas críticas del sistema](#reglas-críticas-del-sistema)
- [Configuración del modelo](#configuración-del-modelo)
- [Guía para futuras iteraciones](#guía-para-futuras-iteraciones)

---

## Arquitectura de prompts

El sistema usa **dos prompts independientes** con responsabilidades distintas:

```
Mensaje del usuario
        ↓
┌─────────────────────────┐
│  INTENT_SYSTEM_PROMPT   │  → JSON: { intent, shipment_id, new_date, ... }
│  (clasificación)        │
└─────────────────────────┘
        ↓
   Orquestador decide handler
        ↓
┌─────────────────────────┐
│  RESPONSE_SYSTEM_PROMPT │  → Texto libre en tono del cliente
│  (generación)           │
└─────────────────────────┘
```

**Por qué dos prompts separados:**
- El prompt de clasificación necesita salida estructurada (JSON) con `temperature=0`
- El prompt de respuesta necesita salida libre con tono del cliente
- Mezclarlos en uno generaba respuestas con JSON en el mensaje al usuario o clasificaciones con lenguaje natural

---

## Prompt de detección de intenciones

### Objetivo

Clasificar el mensaje del usuario en una de 6 intenciones y extraer entidades relevantes en **un solo paso**, devolviendo únicamente JSON válido.

### Estructura del prompt

```
INTENCIONES DISPONIBLES
  → Descripción + ejemplos por intención

EXTRACCIÓN DE ENTIDADES
  → shipment_id, new_date, time_window, language

REGLAS DE DESAMBIGUACIÓN
  → Casos límite entre intenciones similares

FORMATO DE SALIDA
  → Schema JSON obligatorio

EJEMPLOS
  → Pares input/output por intención
```

### Intenciones y criterios de clasificación

| Intención | Criterio principal | Ejemplos de activación |
|---|---|---|
| `STATUS_QUERY` | El usuario quiere saber dónde está un envío | "¿dónde está mi paquete?", "estado del envío 123" |
| `RESCHEDULE` | El usuario quiere cambiar fecha o horario | "reprogramar", "cambiar fecha", "no puedo recibir el martes" |
| `CREATE_TICKET` | El usuario reporta un problema | "llegó dañado", "está tardando", "quiero reportar" |
| `CANCEL` | El usuario quiere cancelar la operación actual | "cancelar", "olvídalo", "stop" |
| `GREETING` | Saludo o comentario social sin intención logística | "hola", "gracias", "ok", "perfecto" |
| `UNKNOWN` | No encaja en ninguna categoría anterior | "¿cuánto cuesta enviar?", "¿tienen sucursal?" |

### Schema de salida

```json
{
  "intent": "STATUS_QUERY",
  "shipment_id": "14309635",
  "new_date": null,
  "time_window": null,
  "language": "es",
  "confidence": "high"
}
```

---

## Prompt de respuesta al usuario

### Objetivo

Generar respuestas en el tono y estilo del cliente configurado, sin inventar datos y sin salirse del rol de asistente logístico.

### Construcción dinámica

El prompt se construye en `build_response_prompt(client_config)` usando los valores del YAML:

```python
f"""Eres {name}, un asistente de soporte logístico de {company}.
Tono: {tone}. Idioma principal: {language}.

REGLAS:
- Nunca inventes datos de envíos, fechas ni estados
- Si no tienes la información, dilo claramente
- Sé conciso. No repitas información innecesariamente
- Si el usuario falla {escalate_after} veces seguidas, escala a un agente humano
"""
```

---

## Iteraciones y problemas resueltos

### Problema 1 — El LLM inventaba shipment_ids

**Observación:** Al decir "necesito ayuda con un paquete" sin mencionar ningún ID, el modelo devolvía `"shipment_id": "14309635"` — un ID que había visto en la sesión o que alucinó.

**Iteraciones:**

```
v1: Sin instrucción explícita
    → Modelo inventa IDs con frecuencia

v2: "Si no hay ID claro, pon null"
    → Reduce pero no elimina el problema

v3: "REGLA CRÍTICA: solo extrae el shipment_id si aparece
     LITERALMENTE en el mensaje. NUNCA inventes, asumas
     ni recuerdes IDs de mensajes anteriores."
    → Mejora significativa, reduce a ~10% de casos
```

**Solución definitiva:** Guardia en código además del prompt:

```python
# agent.py — solo usar el ID si aparece en el mensaje del usuario
raw_id = detection.get("shipment_id")
prefilled_id = raw_id if (raw_id and raw_id in user_message) else None
```

**Aprendizaje:** Los modelos pequeños (3B) no son 100% confiables para instrucciones de negación. Siempre agregar una capa de validación en código.

---

### Problema 2 — GREETING y CANCEL clasificaban como UNKNOWN

**Observación:** Mensajes como "gracias", "ok", "olvídalo" se clasificaban como `UNKNOWN`, disparando el contador de escalación innecesariamente.

**Iteraciones:**

```
v1: Solo 4 intenciones (STATUS, RESCHEDULE, TICKET, UNKNOWN)
    → Saludos y cancelaciones caen en UNKNOWN

v2: Agregar GREETING y CANCEL con ejemplos básicos
    → Mejora pero "ok", "perfecto" siguen como UNKNOWN

v3: Ampliar ejemplos de GREETING:
    "hola", "buenas", "hello", "gracias", "thanks",
    "ok", "perfecto", "listo", "entendido"
    → Clasificación correcta en >95% de casos
```

**Aprendizaje:** Los modelos pequeños necesitan más ejemplos que los modelos grandes. Incluir ejemplos de borde (palabras cortas como "ok", "sí") es más importante que describir el concepto.

---

### Problema 3 — Ambigüedad entre STATUS_QUERY y RESCHEDULE

**Observación:** "¿Cuándo llega mi envío?" a veces se clasificaba como `RESCHEDULE` porque el modelo asociaba "cuándo" con fechas.

**Regla de desambiguación agregada:**

```
REGLA: Si el mensaje es ambiguo entre STATUS_QUERY y RESCHEDULE,
       elegir STATUS_QUERY. El usuario puede querer saber la fecha
       actual sin querer cambiarla.

REGLA: Un número solo (ej: "14309635") → STATUS_QUERY.
       El usuario probablemente responde a la pregunta del bot.
```

**Aprendizaje:** Las reglas de desambiguación explícitas son más efectivas que confiar en que el modelo infiera el contexto.

---

### Problema 4 — El modelo devolvía JSON con markdown

**Observación:** Ollama a veces envolvía el JSON en código markdown:

```
```json
{"intent": "STATUS_QUERY", ...}
```
```

Esto rompía el `json.loads()`.

**Solución en prompt:**

```
Tu única tarea es responder ÚNICAMENTE con un objeto JSON válido.
No agregues texto adicional, explicaciones ni markdown.
```

**Solución en código (defensa en profundidad):**

```python
# llm.py — limpiar markdown antes de parsear
raw = raw.strip()
if raw.startswith("```"):
    raw = re.sub(r"```(?:json)?\n?", "", raw).strip("`").strip()
```

**Aprendizaje:** Siempre limpiar la salida del modelo antes de parsear, independientemente de cuán explícita sea la instrucción.

---

### Problema 5 — Timeout en la primera llamada

**Observación:** La primera llamada al modelo tardaba 45-90 segundos mientras `llama3.2` se cargaba en memoria, superando el timeout de 30s.

**Iteraciones:**

```
v1: timeout=30s, sin reintentos → Error frecuente en primera carga
v2: timeout=60s, sin reintentos → Mejor pero aún falla en hardware lento
v3: timeout=120s, retries=2    → Funciona en todos los entornos probados
```

**Código final:**

```python
def chat(messages, temperature=0.2, retries=2):
    for attempt in range(retries + 1):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
            ...
        except requests.exceptions.Timeout:
            if attempt < retries:
                continue
            raise RuntimeError("Ollama tardó demasiado...")
```

---

### Problema 6 — Extracción de fecha en lenguaje natural

**Observación:** El LLM extraía fechas relativas como "el lunes" o "la próxima semana" en `new_date`, que no pasaban el validator `YYYY-MM-DD`.

**Decisión de diseño:** No convertir fechas relativas a absolutas en el LLM (muy propenso a errores con modelos pequeños). En cambio:

1. Si el LLM extrae una fecha en formato `YYYY-MM-DD` válida → pre-llenar
2. Si extrae texto libre → descartar silenciosamente, el handler la pide de nuevo

```python
# reschedule/handler.py — prefill() con validación
def prefill(self, shipment_id=None, new_date=None, time_window=None):
    if new_date and _valid_date(new_date):        # solo si es YYYY-MM-DD válida
        self.collected["new_date"] = new_date
```

**Aprendizaje:** Es mejor hacer menos con el LLM y delegar la lógica al código. Los modelos pequeños cometen errores predecibles en conversión de formatos.

---

## Reglas críticas del sistema

Estas reglas están en el prompt y son las más importantes para el comportamiento correcto:

### 1. No inventar shipment_ids

```
REGLA CRÍTICA: solo extrae el shipment_id si aparece LITERALMENTE
en el mensaje. Si el mensaje NO contiene un número o código de
envío explícito → SIEMPRE pon null.
NUNCA inventes, asumas ni recuerdes IDs de mensajes anteriores.
```

### 2. Preferir STATUS_QUERY ante ambigüedad

```
REGLA: Si el mensaje es ambiguo entre STATUS_QUERY y RESCHEDULE
       → elegir STATUS_QUERY.
REGLA: Un número solo → STATUS_QUERY.
```

### 3. Solo JSON, sin texto adicional

```
Tu única tarea es analizar el mensaje del usuario y responder
ÚNICAMENTE con un objeto JSON válido.
No agregues texto adicional, explicaciones ni markdown.
```

### 4. Escalar tras N fallos

```
Si el usuario falla {escalate_after} veces seguidas,
escala a un agente humano.
```

---

## Configuración del modelo

### Parámetros actuales

| Parámetro | Valor | Justificación |
|---|---|---|
| `model` | `llama3.2` | Balance entre calidad y velocidad en hardware consumer |
| `temperature` (intent) | `0.0` | Clasificación determinista, sin creatividad |
| `temperature` (response) | `0.2` | Ligera variación en respuestas, mantiene coherencia |
| `timeout` | `120s` | Tolerancia a la carga inicial del modelo |
| `retries` | `2` | Reintentos ante timeout transitorio |
| `max_tokens` | `1024` | Suficiente para respuestas logísticas |

### Por qué llama3.2 (3B)

- Corre en CPU con ~8GB RAM sin GPU
- Tiempo de respuesta aceptable (3-8s por llamada una vez caliente)
- Suficiente para clasificación de intenciones en español
- Modelo más grande (llama3.2:11b) mejoraría calidad pero requiere GPU

### Alternativas evaluadas

| Modelo | Ventaja | Desventaja |
|---|---|---|
| `llama3.2:3b` | Ligero, rápido | Ocasionales errores en ambigüedad |
| `llama3.2:11b` | Mejor comprensión | Requiere GPU, lento en CPU |
| `mistral:7b` | Bueno en español | Más lento que llama3.2:3b |
| `phi3:mini` | Muy rápido | Peor en extracción de entidades |

---

## Guía para futuras iteraciones

### Cómo mejorar la clasificación

1. **Agregar más ejemplos** al `INTENT_SYSTEM_PROMPT` para casos que fallen con frecuencia
2. **Ampliar `NEGATIVE_RESPONSES`** en `StatusHandler` si el follow-up no reconoce nuevas variantes de "no"
3. **Probar con llama3.2:11b** si hay acceso a GPU para reducir errores de ambigüedad

### Cómo agregar una nueva intención

1. Agregar la intención a `INTENT_SYSTEM_PROMPT` con descripción y 3+ ejemplos
2. Agregar regla de desambiguación si hay solapamiento con otra intención
3. Crear el handler correspondiente en `agent/<nueva_intención>/`
4. Agregar el routing en `agent.py → _detect_and_route()`
5. Agregar mensajes al YAML de cada cliente

### Cómo ajustar el tono por cliente

Los prompts de respuesta se construyen dinámicamente desde el YAML. Para cambiar el tono:

```yaml
# templates/cliente_c.yaml
tone: casual        # el prompt usará este valor
name: "BotX"
message_formats:
  greeting: "¡Hola! 👋 Soy BotX..."
```

No es necesario modificar el código — solo el YAML.

### Cómo depurar una clasificación incorrecta

```python
# Probar el prompt directamente
from agent.llm import detect_intent
result = detect_intent("tu mensaje problemático aquí")
print(result)
# → {"intent": "...", "shipment_id": ..., "confidence": "..."}
```

Si `confidence` es `"low"`, el modelo está inseguro y probablemente necesita más ejemplos para ese caso.