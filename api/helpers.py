
from datetime import date, datetime


ORDER_TYPE_LABELS = {
    "PU": "Pickup",
    "DE": "Delivery",
    "CT": "Container Transfer",
}

def derive_status(shipment: dict) -> str:
    fax = shipment["fax"]
    order_type = fax.get("order_type", "")
    date1 = fax.get("date1", "")
    date2 = fax.get("date2", "")

    # Use date1 (pickup/origin date) or date2 (delivery date) to infer status
    ref_date_str = date2 if date2 else date1
    today = date.today()

    if not ref_date_str:
        return "PENDING_SCHEDULE"

    try:
        ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "UNKNOWN"

    if order_type == "PU":
        if ref_date > today:
            return "SCHEDULED_PICKUP"
        return "PICKED_UP"
    elif order_type == "DE":
        if ref_date > today:
            return "IN_TRANSIT"
        return "DELIVERED"
    elif order_type == "CT":
        if ref_date > today:
            return "IN_TRANSIT"
        return "TRANSFERRED"
    return "UNKNOWN"


def build_shipment_response(shipment: dict) -> dict:
    fax = shipment["fax"]
    return {
        "shipment_id": shipment["shipmentid"],
        "status": derive_status(shipment),
        "order_type": ORDER_TYPE_LABELS.get(fax.get("order_type", ""), fax.get("order_type", "")),
        "customer_code": fax.get("customer_code", ""),
        "container": f"{fax.get('container_letters','')} {fax.get('container_numbers','')}".strip(),
        "origin": {
            "name": fax.get("stop1_name", ""),
            "address": fax.get("stop1_add", ""),
            "city": fax.get("stop1_city", ""),
            "state": fax.get("stop1_st", ""),
            "zip": fax.get("stop1_zip", ""),
            "date": fax.get("date1", ""),
            "time": fax.get("time1", ""),
        },
        "destination": {
            "name": fax.get("stop2_name", ""),
            "address": fax.get("stop2_add", ""),
            "city": fax.get("stop2_city", ""),
            "state": fax.get("stop2_st", ""),
            "zip": fax.get("stop2_zip", ""),
            "date": fax.get("date2", ""),
            "time": fax.get("time2", ""),
        },
        "cargo": {
            "pieces": fax.get("pieces", ""),
            "weight_lbs": fax.get("weight", ""),
            "seal": fax.get("seal", ""),
            "bol": fax.get("blbk", ""),
        },
        "financials": {
            "rate": fax.get("rate", ""),
            "fuel_surcharge": fax.get("fuelsurcharge", ""),
        },
        "ramp": fax.get("rampfilter1") or fax.get("rampfilter2") or "",
        "processing": {
            "hour_init": shipment.get("hour_init", ""),
            "hour_end": shipment.get("hour_end", ""),
        },
    }
