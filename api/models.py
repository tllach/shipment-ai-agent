from typing import Optional
from pydantic import BaseModel  


class TicketCreateRequest(BaseModel):
    shipment_id: str
    issue_type: str   
    description: str
    severity: Optional[str] = "MEDIUM"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

class RescheduleRequest(BaseModel):
    new_date: str          # "YYYY-MM-DD"
    time_window: str       # e.g. "08:00-12:00"
    reason: Optional[str] = None