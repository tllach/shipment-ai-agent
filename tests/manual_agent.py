from agent.agent import Agent

agent = Agent()

print("=== LogiBot - Prueba de consola ===")
print("Escribe 'salir' para terminar\n")

# Arrancar
print(f"Bot: {agent.chat('hola')}\n")

while True:
    user = input("Tú: ").strip()
    if user.lower() == "salir":
        break
    response = agent.chat(user)
    print(f"\nBot: {response}\n")