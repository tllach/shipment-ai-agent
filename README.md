# Agent AI

Agente conversacional de soporte logístico construido con Python, FastAPI y Ollama (LLaMA 3.2). Permite a los usuarios consultar el estado de envíos, reprogramar entregas y crear tickets de soporte a través de una interfaz de chat con detección de intenciones mediante LLM local.

---

## Tabla de contenidos

- [Relevancia](#relevancia)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Cómo correr el proyecto](#cómo-correr-el-proyecto)
- [Cómo probar el agente](#cómo-probar-el-agente)
- [Configuración de clientes](#configuración-de-clientes)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Mejoras futuras](#mejoras-futuras)
- [Sobre la autora](#sobre-la-autora)

---

## Relevancia

El soporte al cliente en logística suele ser repetitivo, lento y costoso.

Este agente de IA automatiza:

- Consultas de estado de envíos
- Reprogramación de entregas
- Reporte de problemas (tickets)


## Arquitectura

### Diseño del sistema

```
Usuario → UI (Streamlit)
              ↓
         Agent (orquestador)
              ↓
         LLM (Ollama llama3.2)  ←→  detect_intent()
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
 Status    Ticket   Reschedule
 Handler   Handler   Handler
    └─────────┼─────────┘
              ↓
         Mock API (FastAPI)
              ↓
         shipments.json
```

### Flujo

1. El usuario envía un mensaje
2. El LLM detecta la intención y extrae entidades (shipment_id, fecha, horario)
3. El orquestador activa el handler correspondiente
4. El handler recolecta slots faltantes, valida datos y llama al API
5. La respuesta se formatea según la configuración YAML del cliente

---

## Requisitos


| Componente | Versión mínima | Comentarios |
|---|---|---|
| Python | 3.11 o 3.12 | No usar 3.13+ — pydantic-core no tiene wheels... |
| pip | 23+ |
| Ollama | 0.3+ |

### Dependencias Python

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
streamlit==1.38.0
requests==2.32.3
pyyaml==6.0.2
pydantic==2.9.2
pytest==8.3.3
```

### Modelo LLM

```
llama3.2   (3B parámetros, ~2GB en disco)
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tllach/shipment-ai-agent
cd shipment-ai-agent
```

### 2. Crear y activar el entorno virtual

```bash
# Windows (PowerShell)
py -3.11 -m venv venv
venv\Scripts\activate

# macOS / Linux
py -3.11 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar Ollama y descargar el modelo

```bash
# Instalar Ollama desde https://ollama.com/download
# Luego descargar el modelo (solo la primera vez):
ollama pull llama3.2
```

### 5. Configurar PYTHONPATH

```bash
# Windows (PowerShell) — ejecutar desde la raíz del proyecto
$env:PYTHONPATH = (Get-Location).Path

# macOS / Linux
export PYTHONPATH=$(pwd)
```

---

## Cómo ejecutar el proyecto

Necesitas **3 terminales** corriendo simultáneamente:

### Terminal 1 — Mock API

```bash
uvicorn api.main:app --reload --port 8000
```

Verificar: [http://localhost:8000](http://localhost:8000)  
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

```json
// GET http://localhost:8000 → respuesta esperada:
{
  "service": "Logistics Mock API",
  "version": "1.0.0",
  "shipments_loaded": 77
}
```

### Terminal 2 — Ollama

```bash
ollama serve
```

Verificar: [http://localhost:11434](http://localhost:11434)

> **Nota:** La primera llamada al LLM tarda 30-60 segundos mientras carga el modelo en memoria. Las siguientes son más rápidas. Para pre-calentar el modelo antes de abrir el chat:
> ```bash
> ollama run llama3.2 "hola"
> ```

### Terminal 3 — Interfaz de chat (Streamlit)

```bash
streamlit run ui/app.py
```

Abrir: [http://localhost:8501](http://localhost:8501)

#### Alternativa — Prueba por consola

```bash
python tests/manual_agent.py --client cliente_a
python tests/manual_agent.py --client cliente_b
```

---

## Cómo probar el agente

### Consulta de estado

| Prompt del usuario | Resultado esperado |
|---|---|
| `"¿Dónde está mi paquete?"` | Bot pregunta el número de envío |
| `"Estado del envío 14309635"` | Bot muestra estado, origen, destino, fechas y carga |
| `"track shipment 14324766"` | Bot responde en inglés (detección automática de idioma) |
| `"estado del envío 99999999"` | Bot informa que el envío no existe |

**Ejemplo completo:**
```
Tú:  Estado del envío 14309635
Bot: Estado del envío 14309635
     Estado: Recolectado
     Tipo de operación: Pickup
     Origen: SUBARU OF AMERICA — LEBANON, IN
             Fecha: 2025-01-02 07:30 (hace N días)
     Destino: CSXT - INDIANAPOLIS — AVON, IN
              Fecha estimada: 2025-01-05 (hace N días)
     Carga: 10000 lbs
     ¿Necesita algo más con este envío?
```

---

### Reprogramación de envío

| Prompt del usuario | Resultado esperado |
|---|---|
| `"Quiero reprogramar una entrega"` | Bot pide número de envío |
| `"Reprogramar envío 14309635 para el 2026-05-10"` | Bot pre-llena fecha y pide horario |
| `"ID de envío entregado (DELIVERED)"` | Bot informa que no se puede reprogramar |
| `"cancelar"` en cualquier momento | Bot cancela la operación |

**Ejemplo completo:**
```
Tú:  Quiero reprogramar el envío 14309635
Bot: ¿Cuál es la nueva fecha? (formato: YYYY-MM-DD)
Tú:  2026-05-15
Bot: ¿En qué horario? (formato: HH:MM-HH:MM)
Tú:  8:00-12:00
Bot: ¿Cuál es el motivo de la reprogramación?
Tú:  No estaré en casa ese día
Bot: Voy a realizar la siguiente reprogramación:
     Envío:   14309635
     Fecha:   2026-05-15 (en N días)
     Horario: 08:00-12:00
     Motivo:  No estaré en casa ese día
     ¿Confirma? (SI / NO)
Tú:  si
Bot: ¡Reprogramación realizada con éxito!
```

---

### Creación de ticket

| Prompt del usuario | Resultado esperado |
|---|---|
| `"Mi paquete llegó dañado"` | Bot pide número de envío |
| `"ID de envío inexistente"` | Bot informa que el envío no existe, no pide más datos |
| `"ID con ticket existente"` | Bot informa que ya hay ticket activo, no crea duplicado |
| Email inválido | Bot rechaza y vuelve a pedir el correo |

**Ejemplo completo:**
```
Tú:  Quiero reportar un problema con mi envío
Bot: Por favor proporcione su ID de envío.
Tú:  14309635
Bot: ¿Qué tipo de problema está experimentando?
     Opciones: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS
Tú:  DAÑO
Bot: Por favor describa el problema en detalle.
Tú:  La caja llegó completamente aplastada y el contenido está roto
Bot: ¿Cuál es su correo electrónico de contacto?
Tú:  usuario@email.com
Bot: Voy a crear el siguiente ticket:
     Envío:       14309635
     Problema:    DAÑO
     Descripción: La caja llegó completamente aplastada...
     Email:       usuario@email.com
     ¿Confirma? (SI / NO)
Tú:  si
Bot: Su ticket ha sido creado. Ticket ID: TKT-XXXXXXXX
```

---

### Escenarios de prueba rápida (consola)

Desde `tests/manual_agent.py`, usa los comandos `/test`:

```
/test 1   → Consulta de estado con ID
/test 2   → Consulta de estado sin ID
/test 3   → Crear ticket flujo completo
/test 4   → Reprogramar con fecha en el mensaje
/test 5   → Reprogramar flujo completo
/test 6   → Escalación por intención desconocida
/test 7   → Cancelar operación
/test 8   → Saludo y despedida
```

### Tests automatizados

El proyecto tiene 20 tests distribuidos en 3 archivos. No requieren Ollama ni el Mock API corriendo — todas las llamadas externas están mockeadas.

```bash
python -m pytest tests/ -v
```

Salida esperada:
```
collected 20 items

tests/test_agent.py::test_greeting_devuelve_bienvenida           PASSED
tests/test_agent.py::test_status_query_con_id_prellenado         PASSED
tests/test_agent.py::test_guardia_anti_alucinacion               PASSED
tests/test_agent.py::test_cancel_sin_handler_activo              PASSED
tests/test_agent.py::test_unknown_escala_tras_n_intentos         PASSED
tests/test_agent.py::test_reset_limpia_handler_activo            PASSED
tests/test_agent.py::test_handler_activo_recibe_continuacion     PASSED
tests/test_agent.py::test_reschedule_con_slots_en_mensaje        PASSED
tests/test_reschedule.py::test_flujo_completo_sin_prefill        PASSED
tests/test_reschedule.py::test_prefill_valido_salta_slots        PASSED
tests/test_reschedule.py::test_fecha_invalida_genera_reintento   PASSED
tests/test_reschedule.py::test_envio_delivered_bloquea           PASSED
tests/test_reschedule.py::test_envio_no_encontrado               PASSED
tests/test_status.py::test_pide_shipment_id_si_falta             PASSED
tests/test_status.py::test_respuesta_con_datos_completos         PASSED
tests/test_status.py::test_followup_negativo_cierra_handler      PASSED
tests/test_status.py::test_envio_no_encontrado                   PASSED
tests/test_status.py::test_envio_entregado_muestra_fecha_entrega PASSED
tests/test_status.py::test_error_api_termina_handler             PASSED
tests/test_status.py::test_mensaje_usa_config_yaml               PASSED

20 passed in Xs
```

**Cobertura por archivo:**

| Archivo | Handler | Tests | Qué cubre |
|---|---|---|---|
| `test_agent.py` | Orquestador | 8 | Routing, guardia anti-alucinación, UNKNOWN→escalación, reset, pre-llenado |
| `test_reschedule.py` | RescheduleHandler | 5 | Flujo completo, prefill, fecha inválida, DELIVERED bloqueado, 404 |
| `test_status.py` | StatusHandler | 7 | Respuesta completa, follow-up, DELIVERED, 404, error API, config YAML |

Para correr solo un archivo:
```bash
python -m pytest tests/test_reschedule.py -v
python -m pytest tests/test_status.py -v
python -m pytest tests/test_agent.py -v
```

---

## Configuración de clientes

Cada cliente tiene su propio archivo YAML en `templates/`:

```
templates/
├── cliente_a.yaml   # Tono formal, sin emojis, escala tras 2 intentos
└── cliente_b.yaml   # Tono casual, con emojis, escala tras 3 intentos
```

Para crear un nuevo cliente, copiar cualquier YAML y editar:

```yaml
tone: formal          # formal | casual
language: es          # es | en
name: "MiEmpresa"

policies:
  escalate_after_attempts: 2

message_formats:
  greeting: >
    Bienvenido a {name}. ¿En qué puedo ayudarle?

  # IMPORTANTE:
  # Usar | (literal) para mensajes multilínea con variables
  # Usar > (folded) solo para mensajes de una sola línea lógica
  status_update: |
    Estado del envío {id}: {status}
    Destino: {dest_name} — Fecha: {dest_date} {dest_relative}
```

**Variables disponibles para `status_update`:**

| Variable | Descripción |
|---|---|
| `{id}` | ID del envío |
| `{status}` | Estado (PICKED_UP, IN_TRANSIT, etc.) |
| `{order_type}` | Pickup / Delivery / Container Transfer |
| `{container}` | Número de contenedor |
| `{origin_name}`, `{origin_city}`, `{origin_state}` | Datos de origen |
| `{origin_date}`, `{origin_time}`, `{origin_relative}` | Fecha de origen |
| `{dest_name}`, `{dest_city}`, `{dest_state}` | Datos de destino |
| `{dest_date}`, `{dest_time}`, `{dest_relative}` | Fecha estimada de entrega |
| `{weight}`, `{pieces}`, `{bol}`, `{seal}` | Datos de carga |

Para iniciar el agente con un cliente específico:

```bash
# Consola
python tests/manual_agent.py --client cliente_a

# UI — seleccionar desde el selector en el sidebar
streamlit run ui/app.py
```

---

## Estructura del proyecto

```
ai-agent/
├── agent/
│   ├── agent.py              # Orquestador principal
│   ├── llm.py                # Cliente Ollama + prompt engineering
│   ├── config.py             # Cargador de configuración YAML
│   ├── tools.py              # Capa centralizada de llamadas al API
│   ├── status/
│   │   ├── handler.py        # Handler para consultas de estado
│   │   └── tool_status.py    # Slots, formatter y llamadas al API
│   ├── tickets/
│   │   ├── handler.py        # Handler para creación de tickets
│   │   └── tool_tickets.py   # Slots, validadores y llamadas al API
│   └── reschedule/
│       ├── handler.py        # Handler para reprogramación
│       └── tool_reschedule.py # Slots, validadores y llamadas al API
├── api/
│   ├── main.py               # FastAPI — endpoints REST
│   ├── models.py             # Pydantic models
│   ├── helpers.py            # derive_status(), build_shipment_response()
│   └── shipments.json        # 77 envíos de datos reales
├── docs/
│   ├── SOW.md                # Statement of Work: alcance, supuestos, fuera de alcance
│   ├── RUNBOOK.md            # Operación: cómo reiniciar, dónde ver logs, errores comunes
│   └── PROMPT_NOTES.md       # Iteración y pruebas
├── templates/
│   ├── cliente_a.yaml        # Config cliente formal
│   └── cliente_b.yaml        # Config cliente casual
├── tests/
│   ├── manual_agent.py       # Prueba interactiva por consola
├── ui/
│   └── app.py                # Interfaz Streamlit
└── requirements.txt
```

---

## Notas de desarrollo

- El agente **nunca inventa datos** — si el API no retorna un campo, no lo muestra
- El `shipment_id` detectado por el LLM solo se usa si aparece literalmente en el mensaje del usuario (guardia anti-alucinación)
- Los handlers validan el `shipment_id` **antes** de pedir datos adicionales al usuario
- Timeout del LLM configurado a 120s con 2 reintentos para tolerar la carga inicial del modelo

## Mejoras futuras

- Persistencia de conversaciones (PostgreSQL)
- Despliegue con Docker
- Integración con APIs reales de logística
- Modelo de intención fine-tuned
- Frontend en React (reemplazar Streamlit)

## Sobre la autora

Desarrollado por una Fullstack Developer enfocada en:

- Aplicaciones con IA
- Productos SaaS
- Sistemas backend escalables

Abierta a oportunidades en roles de AI / Fullstack 
