import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from agent.agent import Agent
from agent.config import list_available_clients


st.set_page_config(
    page_title="LogiBot",
    page_icon="🚚",
    layout="centered",
)

# Style 
st.markdown("""
<style>
    /* Font */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Hide streamlit default elements */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 780px; }

    /* Header */
    .logibot-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 1.2rem 1.5rem;
        background: #0f172a;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #3b82f6;
    }
    .logibot-header h1 {
        margin: 0;
        font-size: 1.4rem;
        font-weight: 600;
        color: #f8fafc;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: -0.5px;
    }
    .logibot-header p {
        margin: 0;
        font-size: 0.78rem;
        color: #94a3b8;
    }
    .client-badge {
        margin-left: auto;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.75rem;
        color: #3b82f6;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Chat messages */
    .msg-user {
        display: flex;
        justify-content: flex-end;
        margin: 0.5rem 0;
    }
    .msg-user .bubble {
        background: #3b82f6;
        color: #fff;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.5;
        box-shadow: 0 1px 4px rgba(59,130,246,0.3);
    }
    .msg-bot {
        display: flex;
        justify-content: flex-start;
        margin: 0.5rem 0;
        gap: 10px;
        align-items: flex-end;
    }
    .bot-avatar {
        width: 30px;
        height: 30px;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
    .msg-bot .bubble {
        background: #1e293b;
        color: #e2e8f0;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.5;
        border: 1px solid #334155;
        white-space: pre-wrap;
    }

    /* Input area */
    .stTextInput > div > div > input {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #f1f5f9 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
    }

    /* Selectbox */
    .stSelectbox > div > div {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #f1f5f9 !important;
    }

    /* Buttons */
    .stButton > button {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #94a3b8 !important;
        border-radius: 8px !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.8rem !important;
        transition: all 0.15s !important;
    }
    .stButton > button:hover {
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
    }

    /* Dark background */
    .stApp { background: #0a0f1e; }

    /* Divider */
    hr { border-color: #1e293b; }

    /* Scrollable chat container */
    .chat-container {
        max-height: 520px;
        overflow-y: auto;
        padding: 1rem;
        background: #0f172a;
        border-radius: 12px;
        border: 1px solid #1e293b;
        margin-bottom: 1rem;
    }
    .chat-container::-webkit-scrollbar { width: 4px; }
    .chat-container::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# Session state

def init_session(client_name: str = None):
    """Inicializa o reinicia la sesión del agente."""
    st.session_state.agent    = Agent(client_name=client_name)
    st.session_state.messages = []
    # Mensaje de bienvenida
    greeting = st.session_state.agent.chat("")
    st.session_state.messages.append({"role": "bot", "content": greeting})


if "agent" not in st.session_state:
    init_session()

if "selected_client" not in st.session_state:
    st.session_state.selected_client = None


# Sidebar

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    st.markdown("---")

    # Selector de cliente
    clients      = list_available_clients()
    client_opts  = ["(default)"] + clients
    current_idx  = 0
    if st.session_state.selected_client in clients:
        current_idx = client_opts.index(st.session_state.selected_client)

    selected = st.selectbox(
        "Cliente",
        client_opts,
        index=current_idx,
        help="Cada cliente tiene su propio tono y mensajes.",
    )

    client_name = None if selected == "(default)" else selected

    # Si cambió el cliente → reiniciar sesión
    if client_name != st.session_state.selected_client:
        st.session_state.selected_client = client_name
        init_session(client_name)
        st.rerun()

    st.markdown("---")

    # Botón reset
    if st.button("🔄 Nueva conversación"):
        init_session(st.session_state.selected_client)
        st.rerun()

    st.markdown("---")

    # Info del cliente activo
    agent  = st.session_state.agent
    config = agent.config
    st.markdown(f"**Nombre:** {config.get('name', 'LogiBot')}")
    st.markdown(f"**Tono:** {config.get('tone', 'formal').capitalize()}")
    st.markdown(f"**Idioma:** {config.get('language', 'es').upper()}")


# Header

client_label = st.session_state.selected_client or "default"
st.markdown(f"""
<div class="logibot-header">
    <div>
        <h1>LogiBot</h1>
        <p>Asistente de soporte logístico</p>
    </div>
    <span class="client-badge">{client_label}</span>
</div>
""", unsafe_allow_html=True)


# Chat display

def render_messages():
    html = '<div class="chat-container">'
    for msg in st.session_state.messages:
        content = msg["content"].replace("<", "&lt;").replace(">", "&gt;")
        if msg["role"] == "user":
            html += f'<div class="msg-user"><div class="bubble">{content}</div></div>'
        else:
            html += f'''
            <div class="msg-bot">
                <div class="bot-avatar">🤖</div>
                <div class="bubble">{content}</div>
            </div>'''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

render_messages()


# Input

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "Mensaje",
            placeholder="Escribe tu mensaje aquí...",
            label_visibility="collapsed",
        )
    with col2:
        submitted = st.form_submit_button("Enviar", use_container_width=True)

if submitted and user_input.strip():
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_input.strip()})

    # Obtener respuesta del agente
    with st.spinner(""):
        response = st.session_state.agent.chat(user_input.strip())

    st.session_state.messages.append({"role": "bot", "content": response})
    st.rerun()