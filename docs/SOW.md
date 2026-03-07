# Statement of Work — LogiBot

**Proyecto:** Agente Conversacional Logístico  
**Versión:** 1.0  
**Fecha:** 2026-03-07  

---

## 1. Descripción general

Desarrollo de un agente conversacional de soporte logístico que permite a los usuarios finales consultar el estado de sus envíos, reprogramar entregas y crear tickets de soporte a través de lenguaje natural. El agente opera con un modelo de lenguaje local (LLaMA 3.2 vía Ollama) y expone una interfaz web construida con Streamlit.

---

## 2. Alcance

### 2.1 Mock API (FastAPI)

- Carga de datos reales desde `shipments.json` (77 envíos)
- Derivación dinámica de estado por tipo de operación y fechas (`PU`, `DE`, `CT`)
- Endpoints implementados:
  - `GET /shipments` — listado con filtros por `order_type` y `status`
  - `GET /shipments/{id}` — detalle de un envío
  - `POST /shipments/{id}/reschedule` — reprogramación con validación de fecha futura
  - `POST /tickets` — creación de ticket con validación de `issue_type`
  - `GET /tickets` — listado con filtro por `shipment_id`
- Almacenamiento de tickets en memoria (sin persistencia)

### 2.2 Agente conversacional

- Detección de intenciones con LLaMA 3.2 local vía Ollama:
  - `STATUS_QUERY`, `RESCHEDULE`, `CREATE_TICKET`, `CANCEL`, `GREETING`, `UNKNOWN`
- Extracción de entidades en el mismo paso: `shipment_id`, `new_date`, `time_window`
- Guardia anti-alucinación: el `shipment_id` detectado por el LLM solo se pre-llena si aparece literalmente en el mensaje del usuario
- Tres handlers con flujo de slot-filling, validación y confirmación:
  - **StatusHandler** — consulta, formato detallado, follow-up
  - **TicketHandler** — validación temprana del envío y ticket existente antes de recolectar datos
  - **RescheduleHandler** — validación de estado (bloquea DELIVERED/TRANSFERRED), normalización de horario, pre-llenado validado desde el LLM
- Escalación automática a agente humano tras N intentos fallidos (configurable por cliente)
- Detección automática de idioma (español / inglés)

### 2.3 Sistema de configuración por cliente

- Templates YAML por cliente con tono, idioma, políticas y mensajes personalizados
- Variables disponibles en templates para todos los flujos (status, reschedule, tickets)
- Dos clientes de referencia incluidos: `cliente_a` (formal) y `cliente_b` (casual)
- Fallbacks hardcodeados para todas las claves de mensajes

### 2.4 Interfaz de usuario (Streamlit)

- Chat con burbujas diferenciadas por rol (usuario / agente)
- Selector de cliente con reinicio automático de sesión al cambiar
- Panel de debug en tiempo real: intent detectado, handler activo, slots recolectados, estado del handler, métricas de sesión
- Botón de nueva conversación

### 2.5 Pruebas

- Script de prueba manual interactiva con 8 escenarios predefinidos y comandos de utilidad
- Tests automatizados para RescheduleHandler (5 casos)
- Tests de integración para StatusHandler y el orquestador principal

---

## 3. Supuestos

- El modelo `llama3.2` (3B) tiene capacidad suficiente para detección de intenciones y extracción de entidades en español e inglés con el prompt engineering implementado
- Ollama corre localmente en `localhost:11434`; no se contempla despliegue en nube del LLM
- El Mock API actúa como sustituto de un sistema logístico real; los datos de `shipments.json` son representativos del dominio
- Los tickets se almacenan en memoria durante la sesión del API; al reiniciar el servidor se pierden
- El estado de los envíos se deriva de `order_type` + fechas; no hay sistema de tracking en tiempo real
- Se asume una sola conversación activa por sesión de Streamlit (sin multi-usuario)
- El cliente que configure un YAML es responsable de usar `|` para templates multilínea y `>` para mensajes de una sola línea lógica

---

## 4. Fuera de alcance

| Ítem | Justificación |
|---|---|
| Autenticación de usuarios | No forma parte del ejercicio técnico |
| Persistencia de tickets y conversaciones en base de datos | Se usa almacenamiento en memoria |
| Despliegue en producción (Docker, cloud, HTTPS) | Entorno local de desarrollo |
| Integración con sistema logístico real | Se usa Mock API con datos de prueba |
| Soporte multiusuario simultáneo | Una sesión por instancia de Streamlit |
| Notificaciones (email, SMS, push) | Canal de comunicación fuera del chat |
| Panel de administración para gestión de clientes y YAMLs | Gestión manual de archivos |
| Modelo LLM en la nube (OpenAI, Anthropic, etc.) | Se usa modelo local por diseño |
| Historial persistente de conversaciones entre sesiones | Sin base de datos |
| Soporte para más de 2 idiomas | Solo español e inglés |

---

## 5. Entregables

| Entregable | Estado |
|---|---|
| Mock API (FastAPI) | ✅ Completo |
| Agente conversacional con 3 handlers | ✅ Completo |
| Sistema de configuración YAML por cliente | ✅ Completo |
| Interfaz Streamlit con panel de debug | ✅ Completo |
| Templates de 2 clientes (formal / casual) | ✅ Completo |
| Tests automatizados y script de prueba manual | ✅ Completo |
| README.md | ✅ Completo |
| SOW.md | ✅ Completo |

---

## 6. Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11+ |
| API | FastAPI + Uvicorn | 0.115 / 0.30 |
| LLM | Ollama + LLaMA 3.2 | 0.3+ / 3B |
| UI | Streamlit | 1.38 |
| Config | PyYAML | 6.0 |
| HTTP client | Requests | 2.32 |
| Validación | Pydantic | 2.9 |
| Testing | Pytest | 8.3 |