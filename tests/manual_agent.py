"""
Script de prueba manual para el agente conversacional.
Corre desde la raíz del proyecto:
    python tests/manual_agent.py
    python tests/manual_agent.py --client cliente_b
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent import Agent

# Colores para la terminal
class C:
    USER  = "\033[96m"   # cyan
    BOT   = "\033[92m"   # verde
    INFO  = "\033[93m"   # amarillo
    ERROR = "\033[91m"   # rojo
    RESET = "\033[0m"
    BOLD  = "\033[1m"

# Comandos especiales
COMMANDS = {
    "/salir":   "Terminar la sesión",
    "/reset":   "Reiniciar la conversación",
    "/estado":  "Ver estado interno del agente",
    "/ayuda":   "Mostrar esta ayuda",
    "/cliente": "Cambiar de cliente (ej: /cliente cliente_b)",
}

# Para prueba rapida de flujos comunes
SCENARIOS = {
    "1": {
        "name": "Status Query — con ID",
        "messages": ["¿Dónde está el envío 14309635?"],
    },
    "2": {
        "name": "Status Query — sin ID",
        "messages": ["Quiero saber el estado de mi envío"],
    },
    "3": {
        "name": "Crear Ticket — flujo completo",
        "messages": [
            "Mi paquete llegó dañado",
            "14309635",
            "DAÑO",
            "La caja llegó completamente aplastada y el contenido está roto",
            "test@email.com",
            "si",
        ],
    },
    "4": {
        "name": "Reprogramar — con fecha en el mensaje",
        "messages": ["Necesito reprogramar el envío 1395083 para el 2026-04-15"],
    },
    "5": {
        "name": "Reprogramar — flujo completo",
        "messages": [
            "Quiero reprogramar una entrega",
            "14309635",
            "2026-05-10",
            "08:00-12:00",
            "No estaré en casa ese día",
            "si",
        ],
    },
    "6": {
        "name": "Intención desconocida → escalación",
        "messages": [
            "¿Cuánto cuesta enviar a Medellín?",
            "¿Tienen sucursal en Barranquilla?",
        ],
    },
    "7": {
        "name": "Cancelar operación",
        "messages": ["Quiero crear un ticket", "14309635", "cancelar"],
    },
    "8": {
        "name": "Saludo y despedida",
        "messages": ["Hola", "gracias, eso es todo"],
    },
}


def print_banner(client_name: str):
    print(f"\n{C.BOLD}{'═' * 55}{C.RESET}")
    print(f"{C.BOLD} LogiBot — Prueba Manual del Agente{C.RESET}")
    print(f"{C.INFO}  Cliente: {client_name or 'default (formal)'}{C.RESET}")
    print(f"{C.INFO}  Escribe /ayuda para ver comandos disponibles{C.RESET}")
    print(f"{C.BOLD}{'═' * 55}{C.RESET}\n")


def print_help():
    print(f"\n{C.INFO}── Comandos ──────────────────────────────{C.RESET}")
    for cmd, desc in COMMANDS.items():
        print(f"  {C.BOLD}{cmd:<12}{C.RESET} {desc}")

    print(f"\n{C.INFO}── Escenarios de prueba rápida ───────────{C.RESET}")
    for key, s in SCENARIOS.items():
        print(f"  {C.BOLD}/test {key:<4}{C.RESET} {s['name']}")
    print()


def run_scenario(agent: Agent, scenario_key: str):
    if scenario_key not in SCENARIOS:
        print(f"{C.ERROR}Escenario '{scenario_key}' no existe.{C.RESET}")
        return

    scenario = SCENARIOS[scenario_key]
    print(f"\n{C.INFO}▶ Ejecutando: {scenario['name']}{C.RESET}")
    print(f"{C.INFO}{'─' * 40}{C.RESET}")

    for msg in scenario["messages"]:
        print(f"{C.USER}Tú:{C.RESET} {msg}")
        response = agent.chat(msg)
        print(f"{C.BOT}Bot:{C.RESET} {response}\n")

    print(f"{C.INFO}{'─' * 40}{C.RESET}")
    print(f"{C.INFO}✓ Escenario completado{C.RESET}\n")


def print_agent_state(agent: Agent):
    print(f"\n{C.INFO}── Estado del agente ─────────────────────{C.RESET}")
    print(f"  Cliente:         {agent.client_name or 'default'}")
    print(f"  Tono:            {agent.config.get('tone', 'formal')}")
    print(f"  Handler activo:  {type(agent.active_handler).__name__ if agent.active_handler else 'None'}")
    print(f"  Intención:       {agent.active_intent or 'None'}")
    print(f"  Intentos UNKNOWN:{agent._unknown_count}")
    print(f"  Turnos historial:{len(agent.history)}")
    if agent.active_handler:
        print(f"  Slots recolectados: {agent.active_handler.collected}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Prueba manual del agente LogiBot")
    parser.add_argument("--client", type=str, default=None,
                        help="Nombre del cliente (ej: cliente_a, cliente_b)")
    args = parser.parse_args()

    agent = Agent(client_name=args.client)
    print_banner(args.client)

    # Mostrar saludo inicial
    print(f"{C.BOT}Bot:{C.RESET} {agent.chat('')}\n")

    while True:
        try:
            user_input = input(f"{C.USER}Tú:{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.INFO}Sesión terminada.{C.RESET}")
            break

        if not user_input:
            continue

        # Comandos especiales
        if user_input == "/salir":
            print(f"{C.INFO}¡Hasta luego!{C.RESET}")
            break

        elif user_input == "/reset":
            response = agent.reset()
            print(f"{C.BOT}Bot:{C.RESET} {response}\n")
            print(f"{C.INFO}[Sesión reiniciada]{C.RESET}\n")

        elif user_input == "/estado":
            print_agent_state(agent)

        elif user_input == "/ayuda":
            print_help()

        elif user_input.startswith("/cliente "):
            new_client = user_input.split(" ", 1)[1].strip()
            agent = Agent(client_name=new_client)
            print(f"{C.INFO}[Cliente cambiado a: {new_client}]{C.RESET}")
            print(f"{C.BOT}Bot:{C.RESET} {agent.chat('')}\n")

        elif user_input.startswith("/test "):
            scenario_key = user_input.split(" ", 1)[1].strip()
            run_scenario(agent, scenario_key)

        # Conversación normal
        else:
            response = agent.chat(user_input)
            print(f"{C.BOT}Bot:{C.RESET} {response}\n")


if __name__ == "__main__":
    main()