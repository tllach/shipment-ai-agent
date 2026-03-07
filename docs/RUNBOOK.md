# RUNBOOK — LogiBot

**Versión:** 1.0  
**Fecha:** 2026-03-07  
**Propósito:** Guía operativa para arrancar, reiniciar, monitorear y resolver errores comunes del sistema.

---

## Tabla de contenidos

- [Servicios del sistema](#servicios-del-sistema)
- [Arranque del sistema](#arranque-del-sistema)
- [Reinicio de servicios](#reinicio-de-servicios)
- [Dónde ver logs](#dónde-ver-logs)
- [Verificación de salud](#verificación-de-salud)
- [Errores comunes](#errores-comunes)
- [Checklist de diagnóstico rápido](#checklist-de-diagnóstico-rápido)

---

## Servicios del sistema

El sistema está compuesto por **3 servicios independientes** que deben correr simultáneamente:

| Servicio | Puerto | Proceso | Descripción |
|---|---|---|---|
| Mock API | `8000` | `uvicorn` | REST API con datos de envíos |
| Ollama | `11434` | `ollama serve` | Servidor del modelo LLM local |
| Streamlit UI | `8501` | `streamlit` | Interfaz web del agente |

---

## Arranque del sistema

Abrir **3 terminales** desde la raíz del proyecto (`ai-agent/`) con el entorno virtual activo.

```bash
# Activar entorno virtual primero en cada terminal
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Terminal 1 — Mock API

```bash
uvicorn api.main:app --reload --port 8000
```

Señal de arranque exitoso:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### Terminal 2 — Ollama

```bash
ollama serve
```

Señal de arranque exitoso:
```
Ollama is running
```

> **Primera vez:** descargar el modelo antes de servir:
> ```bash
> ollama pull llama3.2
> ```

### Terminal 3 — Streamlit UI

```bash
streamlit run ui/app.py
```

Señal de arranque exitoso:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### Orden recomendado de arranque

```
1. Ollama serve        (primero — el modelo tarda en cargar)
2. Mock API            (segundo — los handlers lo necesitan)
3. Streamlit UI        (último — depende de los dos anteriores)
```

---

## Reinicio de servicios

### Reiniciar Mock API

```bash
# CTRL+C en la terminal del API, luego:
uvicorn api.main:app --reload --port 8000
```

> ⚠️ Al reiniciar el API se pierden todos los tickets creados en memoria durante la sesión.

### Reiniciar Ollama

```bash
# CTRL+C en la terminal de Ollama, luego:
ollama serve
```

> La primera petición después del reinicio tardará 30-60 segundos mientras recarga el modelo en memoria.

### Reiniciar Streamlit

```bash
# CTRL+C en la terminal de Streamlit, luego:
streamlit run ui/app.py
```

O usar el botón **"🔄 Nueva conversación"** en el sidebar para reiniciar solo la sesión del agente sin reiniciar el servidor.

### Reinicio completo del sistema

```bash
# 1. Detener todos los servicios con CTRL+C en cada terminal
# 2. Arrancar en orden:
ollama serve
# (nueva terminal)
uvicorn api.main:app --reload --port 8000
# (nueva terminal)
streamlit run ui/app.py
```

---

## Dónde ver logs

### Logs del Mock API

Visibles directamente en la terminal donde corre `uvicorn`:

```
INFO:     127.0.0.1:52341 - "GET /shipments/14309635 HTTP/1.1" 200 OK
INFO:     127.0.0.1:52342 - "POST /tickets HTTP/1.1" 201 Created
INFO:     127.0.0.1:52343 - "GET /shipments/99999999 HTTP/1.1" 404 Not Found
```

Para ver el detalle completo de requests y responses, usar Swagger UI:
```
http://localhost:8000/docs
```

### Logs de Ollama

Visibles en la terminal donde corre `ollama serve`:

```
time=... level=INFO source=routes.go msg="request received" method=POST path=/api/chat
time=... level=INFO source=routes.go msg="llama runner started"
```

Para ver el modelo cargado actualmente:
```bash
ollama ps
```

```
NAME            ID              SIZE    PROCESSOR    UNTIL
llama3.2:latest a80c4f17acd5    4.0 GB  100% CPU     4 minutes from now
```

### Logs de Streamlit

Visibles en la terminal donde corre `streamlit`:

```
[INFO] Starting server...
[WARNING] Session state key 'agent' not found  ← normal en primera carga
```

Errores del agente (Python exceptions) aparecen en esta misma terminal con traceback completo.

### Logs del agente (Python)

Los prints de advertencia del agente salen en la terminal de Streamlit:

```python
[Agent] Advertencia: No se encontró configuración para 'cliente_x'. Usando configuración por defecto.
```

Para agregar más logging durante desarrollo, modificar `agent/agent.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Verificación de salud

### Verificar Mock API

```bash
curl http://localhost:8000
```

Respuesta esperada:
```json
{
  "service": "Logistics Mock API",
  "version": "1.0.0",
  "shipments_loaded": 77
}
```

```bash
# Verificar un envío específico
curl http://localhost:8000/shipments/14309635
```

### Verificar Ollama

```bash
curl http://localhost:11434
```

Respuesta esperada:
```
Ollama is running
```

```bash
# Verificar modelo disponible
ollama list
```

```
NAME            ID              SIZE    MODIFIED
llama3.2:latest a80c4f17acd5    2.0 GB  2 weeks ago
```

### Verificar conectividad entre servicios

```bash
# Desde la raíz del proyecto
python -c "
from agent.tools import get_shipment_status
r = get_shipment_status('14309635')
print('API OK' if r['success'] else 'API ERROR:', r)
"
```

```bash
# Verificar LLM
python -c "
from agent.llm import detect_intent
r = detect_intent('hola')
print('LLM OK:', r)
"
```

---

## Errores comunes

### `Connection refused` al llamar al API

**Síntoma:**
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=8000)
```

**Causa:** El Mock API no está corriendo.

**Solución:**
```bash
uvicorn api.main:app --reload --port 8000
```

---

### `Ollama tardó demasiado en responder`

**Síntoma:** El bot responde con `⚠️ Ollama tardó demasiado en responder.`

**Causas posibles:**
1. Ollama no está corriendo
2. Es la primera llamada y el modelo está cargando (normal, tarda 30-60s)
3. El sistema no tiene suficiente RAM para el modelo

**Solución:**
```bash
# 1. Verificar que Ollama corre
curl http://localhost:11434

# 2. Pre-calentar el modelo antes de abrir el chat
ollama run llama3.2 "hola"

# 3. Verificar RAM disponible (llama3.2 necesita ~4GB)
# Windows: Administrador de tareas → Rendimiento → Memoria
# macOS/Linux:
free -h
```

---

### `No module named 'agent'`

**Síntoma:**
```
ModuleNotFoundError: No module named 'agent'
```

**Causa:** `PYTHONPATH` no apunta a la raíz del proyecto.

**Solución:**
```bash
# Windows (PowerShell)
$env:PYTHONPATH = (Get-Location).Path

# macOS / Linux
export PYTHONPATH=$(pwd)

# Verificar
python -c "import agent; print('OK')"
```

---

### `FileNotFoundError: No se encontró configuración para 'X'`

**Síntoma:**
```
FileNotFoundError: No se encontró configuración para 'cliente_x'. Clientes disponibles: ['cliente_a', 'cliente_b']
```

**Causa:** El nombre de cliente no coincide con ningún archivo en `templates/`.

**Solución:**
```bash
# Ver clientes disponibles
ls templates/

# O desde Python
python -c "from agent.config import list_available_clients; print(list_available_clients())"
```

---

### El bot responde `{id}`, `{status}` sin reemplazar variables

**Síntoma:** El mensaje muestra los placeholders sin reemplazar:
```
Tu envío {id} está en estado {status}.
```

**Causa:** El template en el YAML usa `>` (folded) en vez de `|` (literal) para un mensaje multilínea.

**Solución:** Editar el YAML del cliente y cambiar `>` por `|` en templates con múltiples líneas y variables:

```yaml
# Incorrecto para templates multilínea
status_update: >
  Tu envío {id}
  Estado: {status}

# Correcto
status_update: |
  Tu envío {id}
  Estado: {status}
```

---

### Puerto ya en uso

**Síntoma:**
```
ERROR:    [Errno 48] Address already in use
```

**Solución:**
```bash
# Windows — encontrar y matar el proceso en el puerto 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS / Linux
lsof -ti:8000 | xargs kill -9

# Para Streamlit (puerto 8501)
lsof -ti:8501 | xargs kill -9
```

---

### `KeyError` al procesar respuesta del agente

**Síntoma:** Traceback en la terminal de Streamlit con `KeyError` en algún handler.

**Causa más común:** El API devolvió una estructura inesperada o el slot `collected` no tiene la clave esperada.

**Diagnóstico:**
```bash
# Verificar la respuesta cruda del API
curl http://localhost:8000/shipments/<ID>
curl http://localhost:8000/tickets?shipment_id=<ID>
```

---

### Streamlit no recarga al cambiar código

**Síntoma:** Los cambios en el código no se reflejan en el navegador.

**Solución:**
```bash
# CTRL+C y reiniciar
streamlit run ui/app.py

# O forzar recarga en el navegador: CTRL+SHIFT+R
```

---

## Checklist de diagnóstico rápido

Antes de reportar cualquier error, verificar:

```
□ ¿Está corriendo el Mock API?     → curl http://localhost:8000
□ ¿Está corriendo Ollama?          → curl http://localhost:11434
□ ¿Está cargado el modelo?         → ollama list
□ ¿Está activo el entorno virtual? → which python (debe apuntar a venv/)
□ ¿Está configurado PYTHONPATH?    → python -c "import agent"
□ ¿Existe el cliente en templates? → ls templates/
□ ¿El YAML usa | para multilínea?  → revisar templates/*.yaml
```

Si todos los checks pasan y el error persiste, revisar el traceback completo en la terminal de Streamlit.

---

## Referencia rápida de puertos

| Servicio | URL | Uso |
|---|---|---|
| Mock API | `http://localhost:8000` | Health check |
| Swagger UI | `http://localhost:8000/docs` | Probar endpoints manualmente |
| Ollama | `http://localhost:11434` | Health check |
| Streamlit | `http://localhost:8501` | Interfaz del agente |