"""
Capa centralizada de llamadas al API logístico.
Todos los handlers importan desde aquí — nunca llaman al API directamente.
"""

import requests

API_BASE = "http://localhost:8000"


def get_shipment_status(shipment_id: str) -> dict:
    """GET /shipments/{id}"""
    try:
        resp = requests.get(f"{API_BASE}/shipments/{shipment_id}", timeout=5)
        if resp.status_code == 404:
            return {
                "success": False,
                "not_found": True,
                "error": f"No encontré ningún envío con el ID '{shipment_id}'. Verifica que el número sea correcto.",
            }
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except requests.exceptions.ConnectionError:
        return {"success": False, "not_found": False, "error": "No pude conectarme al sistema logístico. Intenta más tarde."}
    except requests.exceptions.Timeout:
        return {"success": False, "not_found": False, "error": "El sistema tardó demasiado. Intenta de nuevo."}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "not_found": False, "error": str(e)}


def reschedule_shipment(shipment_id: str, new_date: str, time_window: str, reason: str = None) -> dict:
    """POST /shipments/{id}/reschedule"""
    payload = {
        "new_date": new_date,
        "time_window": time_window,
        "reason": reason,
    }
    try:
        resp = requests.post(f"{API_BASE}/shipments/{shipment_id}/reschedule", json=payload, timeout=5)
        resp.raise_for_status()
        return {"success": True, "data": resp.json(), "updated": resp.json().get("updated", {})}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No pude conectarme al sistema logístico. Intenta más tarde."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"success": False, "error": detail}


def create_ticket_api(payload: dict) -> dict:
    """POST /tickets"""
    try:
        resp = requests.post(f"{API_BASE}/tickets", json=payload, timeout=5)
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No pude conectarme al sistema logístico. Intenta más tarde."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"success": False, "error": detail}


def get_tickets_for_shipment(shipment_id: str) -> dict:
    """GET /tickets?shipment_id=..."""
    try:
        resp = requests.get(f"{API_BASE}/tickets", params={"shipment_id": shipment_id}, timeout=5)
        resp.raise_for_status()
        return {"success": True, "data": resp.json().get("tickets", [])}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No pude conectarme al sistema logístico."}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": str(e)}
