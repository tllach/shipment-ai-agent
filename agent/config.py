import os
import yaml
from typing import Optional

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def load_client_config(client_name: str) -> dict:
    """
    Carga el YAML del cliente por nombre.
    Ej: load_client_config("cliente_a") → carga templates/cliente_a.yaml

    Raises FileNotFoundError si no existe el cliente.
    """
    path = os.path.join(TEMPLATES_DIR, f"{client_name}.yaml")

    if not os.path.exists(path):
        available = list_available_clients()
        raise FileNotFoundError(
            f"No se encontró configuración para '{client_name}'. "
            f"Clientes disponibles: {available}"
        )

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def list_available_clients() -> list[str]:
    """Retorna los nombres de los clientes disponibles."""
    if not os.path.exists(TEMPLATES_DIR):
        return []
    return [
        f.replace(".yaml", "")
        for f in os.listdir(TEMPLATES_DIR)
        if f.endswith(".yaml")
    ]


def get_message(config: dict, key: str, **kwargs) -> str:
    """
    Obtiene un mensaje formateado del config del cliente.

    Args:
        config:  dict cargado del YAML
        key:     clave del mensaje (ej: "status_update")
        **kwargs: variables para formatear (ej: id="123", status="IN_TRANSIT")

    Returns:
        Mensaje formateado, o string vacío si la clave no existe.
    """
    template = config.get("message_formats", {}).get(key, "")
    if not template:
        return ""
    try:
        return template.strip().format(**kwargs)
    except KeyError as e:
        # Variable faltante → loguear y usar format_map con fallback a string vacío
        import re
        # Reemplazar variables no provistas con cadena vacía
        filled = template.strip()
        for placeholder in re.findall(r"{(\w+)}", filled):
            if placeholder not in kwargs:
                filled = filled.replace("{" + placeholder + "}", "")
        try:
            return filled.format(**kwargs)
        except Exception:
            return filled


def get_policy(config: dict, key: str, default=None):
    """
    Obtiene el valor de una política del cliente.

    Ej: get_policy(config, "escalate_after_attempts") → 2
    """
    return config.get("policies", {}).get(key, default)


def get_tone(config: dict) -> str:
    """Retorna el tono del cliente: 'formal' o 'casual'."""
    return config.get("tone", "formal")


def get_language(config: dict) -> str:
    """Retorna el idioma principal del cliente."""
    return config.get("language", "es")