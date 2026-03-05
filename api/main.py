from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
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


# Models

class TicketCreateRequest(BaseModel):
    shipment_id: str
    issue_type: str        # e.g. "DAMAGE", "DELAY", "MISSING", "OTHER"
    description: str
    severity: Optional[str] = "MEDIUM"   # LOW / MEDIUM / HIGH / CRITICAL
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None



# Routes 
@app.get("/")
def root():
    return {
        "service": "Logistics Mock API",
        "version": "1.0.0",
        "shipments_loaded": len(SHIPMENTS),
        "endpoints": [
            "POST /tickets",
            "GET  /tickets",
        ],
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
    valid_issue_types = {"DAMAGE", "DELAY", "MISSING", "WRONG_DELIVERY", "BILLING", "OTHER"}
    if body.issue_type.upper() not in valid_issue_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid issue_type '{body.issue_type}'. Valid options: {sorted(valid_issue_types)}",
        )

    # Validate severity
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    severity = (body.severity or "MEDIUM").upper()
    if severity not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{body.severity}'. Valid options: {sorted(valid_severities)}",
        )

    ticket = {
        "ticket_id": f"TKT-{str(uuid.uuid4())[:8].upper()}",
        "shipment_id": body.shipment_id,
        "issue_type": body.issue_type.upper(),
        "description": body.description,
        "severity": severity,
        "contact_email": body.contact_email,
        "contact_phone": body.contact_phone,
        "status": "OPEN",
        "created_at": datetime.now().isoformat() + "Z",
    }

    TICKETS.append(ticket)

    return {
        "success": True,
        "message": "Ticket created successfully. Our team will contact you shortly.",
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



