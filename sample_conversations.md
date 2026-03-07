# Sample Conversations — LogiBot

**Versión:** 1.0  
**Fecha:** 2026-03-07  
**Propósito:** Evidencia de conversaciones del agente cubriendo flujo feliz, datos faltantes y casos límite.

---

## Convenciones

```
👤  Usuario
🤖  LogiBot
[intent]    intención detectada por el LLM
[slot]      slot recolectado o validado
[api]       llamada al Mock API
```

Los mensajes del bot reproducen exactamente los textos de los YAML de cada cliente y los fallbacks del código. Las preguntas de slots vienen de `tool_*.py`.

---

## 1. Flujo feliz — Consulta de estado (cliente_a, formal)

El usuario da el ID en el primer mensaje. El agente consulta el API y cierra.

```
👤  Estado del envío 14309635

    [intent: STATUS_QUERY | shipment_id: "14309635" pre-llenado]
    [api: GET /shipments/14309635 → 200 OK]

🤖  Estado del envío 14309635
    Estado: Recolectado
    Tipo de operación: Pickup
    Contenedor: UMXU 785234
    Origen: SUBARU OF AMERICA — LEBANON, IN
     2025-01-02 a las 07:30 (hace 429 días)
    Destino: CSXT - INDIANAPOLIS — AVON, IN
     Fecha estimada: 2025-01-05 (hace 426 días)
    Carga: 10000 lbs
    BOL: 98765 | Sello: S-112

    ¿Necesita algo más con este envío?

👤  No, gracias

    [NEGATIVE_RESPONSES match → farewell]

🤖  Ha sido un placer asistirle. Que tenga un excelente día.
    No dude en contactarnos si necesita ayuda adicional.
```

---

## 2. Flujo feliz — Reprogramación completa (cliente_b, casual)

El usuario da el ID y la fecha en el primer mensaje. El agente pre-llena ambos y pide solo los datos faltantes.

```
👤  Quiero reprogramar el envío 1395083 para el 2026-05-10

    [intent: RESCHEDULE | shipment_id: "1395083" | new_date: "2026-05-10"]
    [prefill: shipment_id ✓, new_date ✓ (fecha futura válida)]
    [api: GET /shipments/1395083 → status IN_TRANSIT → OK]

🤖  ¿En qué horario? (formato: HH:MM-HH:MM, ej: 08:00-12:00)

👤  8:00-14:00

    [normalize: "8:00-14:00" → "08:00-14:00" ✓]

🤖  ¿Cuál es el motivo de la reprogramación?

👤  No estaré disponible en la fecha original

🤖  Voy a realizar la siguiente reprogramación:

    Envío:   1395083
    Fecha:   2026-05-10 (en 64 días)
    Horario: 08:00-14:00
    Motivo:  No estaré disponible en la fecha original

    ¿Confirma la reprogramación?
    Responda SI para confirmar o NO para modificar algún dato.

👤  SI

    [api: POST /shipments/1395083/reschedule → 200 OK]

🤖  ¡Listo! 🎉 Tu envío 1395083 quedó reprogramado para el 2026-05-10
    en el horario 08:00-14:00. Te avisaremos cuando esté confirmado.
```

---

## 3. Flujo feliz — Creación de ticket (cliente_a, formal)

```
👤  Quiero reportar un problema

    [intent: CREATE_TICKET]

🤖  Por favor, proporcione su ID de envío para que podamos localizar su pedido.

👤  14309635

    [api: GET /shipments/14309635 → 200 OK ✓]
    [api: GET /tickets?shipment_id=14309635 → sin tickets ✓]

🤖  ¿Qué tipo de problema está experimentando?
    Opciones: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS

👤  DAÑO

🤖  Por favor, describa el problema en detalle.

👤  La caja llegó con la esquina aplastada y el contenido roto

🤖  ¿Cuál es su dirección de correo electrónico para que podamos seguir con usted?

👤  cliente@empresa.com

🤖  Voy a crear el siguiente ticket:

    Envío:       14309635
    Problema:    DAÑO
    Descripción: La caja llegó con la esquina aplastada y el contenido roto
    Email:       cliente@empresa.com

    ¿Confirma que desea crear este ticket?
    Responda SI para confirmar o NO para modificar.

👤  SI

    [api: POST /tickets → 201 Created]

🤖  Hemos registrado su caso con el ticket ID TKT-A3F2B1C4.
    Nuestro equipo de soporte se pondrá en contacto con usted a la brevedad
    en la dirección cliente@empresa.com.
```

---

## 4. Datos faltantes — Agente recolecta todos los slots (cliente_a, formal)

El usuario expresa intención sin dar ningún dato. Incluye reintento por fecha inválida.

```
👤  Quiero reprogramar una entrega

    [intent: RESCHEDULE | shipment_id: null]

🤖  ¿Cuál es el número de envío que deseas reprogramar?

👤  es el 14309635

    [api: GET /shipments/14309635 → status PICKED_UP → OK]

🤖  ¿Cuál es la nueva fecha para el envío? (formato: YYYY-MM-DD, ej: 2025-04-15)

👤  el próximo lunes

    [_valid_date("el próximo lunes") → False | attempts: 1]

🤖  La fecha no es válida o ya pasó. Usa el formato YYYY-MM-DD con una fecha futura.

    ¿Cuál es la nueva fecha para el envío? (formato: YYYY-MM-DD, ej: 2025-04-15)

👤  2026-04-20

    [_valid_date("2026-04-20") → True ✓]

🤖  ¿En qué horario? (formato: HH:MM-HH:MM, ej: 08:00-12:00)

👤  09:00-13:00

🤖  ¿Cuál es el motivo de la reprogramación?

👤  Reunión de trabajo ese día

🤖  Voy a realizar la siguiente reprogramación:

    Envío:   14309635
    Fecha:   2026-04-20 (en 44 días)
    Horario: 09:00-13:00
    Motivo:  Reunión de trabajo ese día

    ¿Confirma la reprogramación?
    Responda SI para confirmar o NO para modificar algún dato.

👤  SI

🤖  Su solicitud de reprogramación para el envío 14309635 ha sido confirmada
    para el 2026-04-20 en la franja horaria 09:00-13:00.
    Recibirá una notificación de confirmación a la brevedad.
```

---

## 5. Datos faltantes — Edición antes de confirmar (cliente_b, casual)

El usuario corrige un dato en la pantalla de confirmación.

```
👤  Crear ticket para el 14324766

    [intent: CREATE_TICKET | shipment_id: "14324766" pre-llenado]
    [api: GET /shipments/14324766 → OK, sin tickets previos]

🤖  ¿Qué tipo de problema está experimentando?
    Opciones: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS

👤  RETRASO

🤖  Por favor, describa el problema en detalle.

👤  Lleva 5 días sin actualizaciones y no sé dónde está mi envío

🤖  ¿Cuál es su dirección de correo electrónico para que podamos seguir con usted?

👤  mimail@correo.com

🤖  Voy a crear el siguiente ticket:

    Envío:       14324766
    Problema:    RETRASO
    Descripción: Lleva 5 días sin actualizaciones y no sé dónde está mi envío
    Email:       mimail@correo.com

    ¿Confirma que desea crear este ticket?
    Responda SI para confirmar o NO para modificar.

👤  no, quiero cambiar el correo

    [awaiting_edit_choice: True]

🤖  ¿Qué dato desea corregir?

    1. Tipo de problema (DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS)
    2. Descripción
    3. Correo electrónico

    Escriba el número o el nombre del campo.

👤  3

🤖  Por favor ingrese el nuevo valor.

    ¿Cuál es su dirección de correo electrónico para que podamos seguir con usted?

👤  correcto@empresa.com

🤖  Voy a crear el siguiente ticket:

    Envío:       14324766
    Problema:    RETRASO
    Descripción: Lleva 5 días sin actualizaciones y no sé dónde está mi envío
    Email:       correcto@empresa.com

    ¿Confirma que desea crear este ticket?
    Responda SI para confirmar o NO para modificar.

👤  si

    [api: POST /tickets → 201 Created]

🤖  ¡Listo! Creamos tu ticket con el ID TKT-9D4E2F1A 🎫.
    Nuestro equipo te contactará pronto al correo correcto@empresa.com.
    Lamentamos los inconvenientes.
```

---

## 6. Caso límite — Envío no existe (cliente_a y cliente_b)

```
── cliente_a ──────────────────────────────────────────────

👤  Estado del envío 99999999

    [api: GET /shipments/99999999 → 404]

🤖  Lamentamos informarle que no encontramos ningún envío con el ID 99999999.
    Por favor verifique el número e intente nuevamente.

── cliente_b ──────────────────────────────────────────────

👤  Estado del envío 99999999

    [api: GET /shipments/99999999 → 404]

🤖  Hmm, no encontré ningún envío con el ID 99999999 🤔.
    ¿Puedes verificar el número e intentarlo de nuevo?
```

---

## 7. Caso límite — Reprogramar envío entregado (cliente_b, casual)

```
👤  Reprogramar envío 14324766

    [intent: RESCHEDULE | shipment_id: "14324766" pre-llenado]
    [api: GET /shipments/14324766 → status: DELIVERED]
    [DELIVERED ∈ NON_RESCHEDULABLE_STATUSES → bloquear]

🤖  El envío 14324766 no puede reprogramarse porque ya está en estado
    Entregado.

    Si tienes algún problema con este envío, puedo ayudarte a crear un ticket de soporte.

👤  sí, quiero crear un ticket

    [intent: CREATE_TICKET → nuevo handler]

🤖  Por favor, proporcione su ID de envío para que podamos localizar su pedido.
```

---

## 8. Caso límite — Ticket duplicado (cliente_a, formal)

```
👤  Quiero abrir un caso para el envío 14309635

    [intent: CREATE_TICKET]

🤖  Por favor, proporcione su ID de envío para que podamos localizar su pedido.

👤  14309635

    [api: GET /shipments/14309635 → OK]
    [api: GET /tickets?shipment_id=14309635 → 1 ticket existente → bloquear]

🤖  Ya existe un ticket activo para el envío 14309635.
    Nuestro equipo ya está atendiendo su caso.
```

---

## 9. Caso límite — Cancelación en medio de flujo (cliente_b, casual)

```
👤  Necesito crear un ticket

    [intent: CREATE_TICKET]

🤖  Por favor, proporcione su ID de envío para que podamos localizar su pedido.

👤  14309635

    [api: validación OK]

🤖  ¿Qué tipo de problema está experimentando?
    Opciones: DAÑO, RETRASO, PEDIDO_FALTANTE, ENTREGA_ERRÓNEA, FACTURACIÓN, OTROS

👤  cancelar

    [msg ∈ CANCEL_WORDS → done: True]

🤖  ¡Cancelado! ¿Hay algo más en lo que te pueda ayudar? 😊

👤  no gracias

    [intent: GREETING → farewell]

🤖  ¡Fue un placer ayudarte! 👋 Si necesitas algo más, aquí estamos.
```

---

## 10. Caso límite — Escalación por intenciones desconocidas (cliente_a, escalate_after: 2)

```
👤  ¿Cuánto cuesta enviar un paquete a Bogotá?

    [intent: UNKNOWN | _unknown_count: 1 / max: 2]

🤖  No hemos podido identificar su solicitud. Le invitamos a reformularla.
    Nuestras opciones disponibles son: consultar estado, reprogramar envío
    o reportar un problema.

👤  ¿Tienen oficinas en Medellín?

    [intent: UNKNOWN | _unknown_count: 2 → escalar, reset a 0]

🤖  Estimado cliente, hemos escalado su caso a un agente humano
    quien se pondrá en contacto con usted a la brevedad.
    Disculpe los inconvenientes.
```

---

## Resumen de cobertura

| # | Escenario | Cliente | Resultado |
|---|---|---|---|
| 1 | Consulta de estado con ID directo | cliente_a | ✅ |
| 2 | Reschedule con ID+fecha pre-llenados | cliente_b | ✅ |
| 3 | Ticket flujo completo | cliente_a | ✅ |
| 4 | Reschedule sin datos + fecha inválida | cliente_a | ✅ |
| 5 | Ticket con edición antes de confirmar | cliente_b | ✅ |
| 6 | Envío no existe | ambos | ✅ |
| 7 | Reprogramar envío DELIVERED | cliente_b | ✅ |
| 8 | Ticket duplicado | cliente_a | ✅ |
| 9 | Cancelación en medio de flujo | cliente_b | ✅ |
| 10 | Escalación por UNKNOWN | cliente_a | ✅ |