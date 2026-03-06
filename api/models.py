from typing import Optional
from pydantic import BaseModel  


class TicketCreateRequest(BaseModel):
    shipment_id: str
    issue_type: str   
    description: str
    severity: Optional[str] = "MEDIUM"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

