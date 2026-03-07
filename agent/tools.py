
import requests

API_BASE = "http://localhost:8000"


# reusable API calls 

def get_shipment_status(shipment_id: str) -> dict:
    """
    Llama a GET /shipments/{shipment_id}.
    Retorna dict con success + data o error.
    NUNCA inventa datos — si el API retorna 404, lo reporta tal cual.
    """
    try:
        resp = requests.get(f"{API_BASE}/shipments/{shipment_id}", timeout=5)

        if resp.status_code == 404:
            return {
                "success": False,
                "not_found": True,
                "error": f"No encontré ningún envío con el ID que proporcionaste. "
                        "Verifica que el número sea correcto.",
            }

        resp.raise_for_status()
        return {"success": True, "data": resp.json()}

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "not_found": False,
            "error": "No pude conectarme al sistema logístico. Intenta de nuevo más tarde.",
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "not_found": False,
            "error": "El sistema tardó demasiado en responder. Intenta de nuevo.",
        }
    except requests.exceptions.HTTPError as e:
        return {"success": False, "not_found": False, "error": str(e)}
