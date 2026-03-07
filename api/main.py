from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, date
import json
import uuid
import os


app = FastAPI(
    title="Logistics Mock API",
    description="Mock API for the logistics conversational agent technical assessment.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load shipments at startup 

DATA_PATH = os.path.join(os.path.dirname(__file__), "shipments.json")

with open(DATA_PATH, "r") as f:
    raw = json.load(f)


# Index by shipmentid (last record wins if duplicates exist)
SHIPMENTS: dict[str, dict] = {}
for s in raw:
    sid = s["shipmentid"]
    SHIPMENTS[sid] = s

# In-memory ticket store
TICKETS: list[dict] = []

# Helpers and Models
from api.helpers import derive_status, build_shipment_response;
from api.models import TicketCreateRequest, RescheduleRequest;

# Routes 
@app.get("/")
def root():
    return {
        "service": "Logistics Mock API",
        "version": "1.0.0",
        "shipments_loaded": len(SHIPMENTS),
        "endpoints": [
            "GET  /shipments",
            "GET  /shipments/{shipment_id}",
            "POST /shipments/{shipment_id}/reschedule",
            "POST /tickets",
            "GET  /tickets",
        ],
    }

@app.get("/shipments")
def list_shipments(
    order_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """List all shipments with optional filters."""
    results = []
    for shipment in SHIPMENTS.values():
        fax = shipment["fax"]
        # Filter by order_type
        if order_type and fax.get("order_type", "").upper() != order_type.upper():
            continue
        built = build_shipment_response(shipment)
        # Filter by derived status
        if status and built["status"].upper() != status.upper():
            continue
        results.append(built)

    return {"total": len(results), "shipments": results}


@app.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    """Get status, ETA, location, and details for a specific shipment."""
    shipment = SHIPMENTS.get(shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment '{shipment_id}' not found. Please verify the shipment ID.",
        )
    return build_shipment_response(shipment)


@app.post("/shipments/{shipment_id}/reschedule")
def reschedule_shipment(shipment_id: str, body: RescheduleRequest):
    """Reschedule pickup or delivery. Returns confirmation or validation error."""
    shipment = SHIPMENTS.get(shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment '{shipment_id}' not found.",
        )

    # Validate: new_date must not be in the past
    try:
        new_dt = datetime.strptime(body.new_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD (e.g. 2025-03-15).",
        )

    if new_dt < date.today():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reschedule to a past date ({body.new_date}). Please provide a future date.",
        )
        

    # Apply the change in memory
    order_type = shipment["fax"].get("order_type", "")
    
    if order_type == "PU":
        shipment["fax"]["date1"] = body.new_date
        shipment["fax"]["time1"] = body.time_window
        updated_stop = "pickup"
    else:
        shipment["fax"]["date2"] = body.new_date
        shipment["fax"]["time2"] = body.time_window
        updated_stop = "delivery"

    return {
        "success": True,
        "shipment_id": shipment_id,
        "message": f"Shipment {shipment_id} {updated_stop} rescheduled successfully.",
        "updated": {
            "new_date": body.new_date,
            "time_window": body.time_window,
            "reason": body.reason,
            "rescheduled_at": datetime.now().isoformat() + "Z",
        },
        "new_status": derive_status(shipment),
    }


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketCreateRequest):
    """Create a support ticket linked to a shipment."""
    # Validate shipment exists
    if body.shipment_id not in SHIPMENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment '{body.shipment_id}' not found. Cannot create ticket.",
        )

    # Validate issue_type
    valid_issue_types = {"DAÑO", "RETRASO", "PEDIDO_FALTANTE", "ENTREGA_ERRÓNEA", "FACTURACIÓN", "OTROS"}
    if body.issue_type.upper() not in valid_issue_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid issue_type '{body.issue_type}'. Valid options: {sorted(valid_issue_types)}",
        )
    
    
    ticket = {
        "ticket_id": f"TKT-{str(uuid.uuid4())[:8].upper()}",
        "shipment_id": body.shipment_id,
        "issue_type": body.issue_type.upper(),
        "description": body.description,
        "contact_email": body.contact_email,
        "contact_phone": body.contact_phone,
        "status": "OPEN",
        "created_at": datetime.now().isoformat() + "Z",
    }

    TICKETS.append(ticket)

    return {
        "success": True,
        "message": "El tiquete ha sido creado exitosamente.",
        "ticket": ticket,
    }


@app.get("/tickets")
def list_tickets(shipment_id: Optional[str] = None):
    """List all support tickets, optionally filtered by shipment_id."""
    if shipment_id:
        result = [t for t in TICKETS if t["shipment_id"] == shipment_id]
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No tickets found for shipment_id '{shipment_id}'.",
            )
    else:
        result = TICKETS
    return {"total": len(result), "tickets": result}



