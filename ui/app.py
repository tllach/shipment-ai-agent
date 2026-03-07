"""
Interfaz de chat con Streamlit — Panel lateral + intent + handler + reset.
Corre desde la raíz del proyecto:
    streamlit run ui/app.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from agent.agent import Agent
from agent.config import list_available_clients

st.set_page_config(
    page_title="LogiBot",
    page_icon="🚚",
    layout="wide",
)

# styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* Header */
    .logibot-header {
        display: flex; align-items: center; gap: 12px;
        padding: 1rem 1.5rem; background: #0f172a;
        border-radius: 12px; margin-bottom: 1rem;
        border-left: 4px solid #3b82f6;
    }
    .logibot-header h1 {
        margin: 0; font-size: 1.3rem; font-weight: 600;
        color: #f8fafc; font-family: 'IBM Plex Mono', monospace; letter-spacing: -0.5px;
    }
    .logibot-header p { margin: 0; font-size: 0.75rem; color: #94a3b8; }
    .client-badge {
        margin-left: auto; background: #1e293b; border: 1px solid #334155;
        border-radius: 6px; padding: 4px 10px; font-size: 0.72rem;
        color: #3b82f6; font-family: 'IBM Plex Mono', monospace;
    }

    /* Chat bubbles */
    .msg-user { display: flex; justify-content: flex-end; margin: 0.4rem 0; }
    .msg-user .bubble {
        background: #3b82f6; color: #fff; padding: 10px 16px;
        border-radius: 18px 18px 4px 18px; max-width: 80%;
        font-size: 0.88rem; line-height: 1.5;
        box-shadow: 0 1px 4px rgba(59,130,246,0.3);
    }
    .msg-bot { display: flex; justify-content: flex-start; margin: 0.4rem 0; gap: 8px; align-items: flex-end; }
    .bot-avatar {
        width: 28px; height: 28px; background: #0f172a; border: 1px solid #334155;
        border-radius: 50%; display: flex; align-items: center;
        justify-content: center; font-size: 0.8rem; flex-shrink: 0;
    }
    .msg-bot .bubble {
        background: #1e293b; color: #e2e8f0; padding: 10px 16px;
        border-radius: 18px 18px 18px 4px; max-width: 80%;
        font-size: 0.88rem; line-height: 1.5;
        border: 1px solid #334155; white-space: pre-wrap;
    }

    /* Chat container */
    .chat-container {
        height: 500px; overflow-y: auto; padding: 1rem;
        background: #0f172a; border-radius: 12px;
        border: 1px solid #1e293b; margin-bottom: 0.8rem;
    }
    .chat-container::-webkit-scrollbar { width: 3px; }
    .chat-container::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }

    /* Input */
    .stTextInput > div > div > input {
        background: #1e293b !important; border: 1px solid #334155 !important;
        border-radius: 10px !important; color: #f1f5f9 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.88rem !important; padding: 0.6rem 1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
    }
    
    .typing {
        display: inline-flex;
        gap: 4px;
    }

    .typing span {
        width: 6px;
        height: 6px;
        background: #94a3b8;
        border-radius: 50%;
        animation: blink 1.4s infinite both;
    }

    .typing span:nth-child(2) {
        animation-delay: .2s;
    }

    .typing span:nth-child(3) {
        animation-delay: .4s;
    }

    @keyframes blink {
        0% {opacity:.2}
        20% {opacity:1}
        100% {opacity:.2}
    }

    /* Selectbox */
    .stSelectbox > div > div {
        background: #1e293b !important; border: 1px solid #334155 !important;
        border-radius: 8px !important; color: #f1f5f9 !important;
    }

    /* Buttons */
    .stButton > button {
        background: #1e293b !important; border: 1px solid #334155 !important;
        color: #94a3b8 !important; border-radius: 8px !important;
        font-size: 0.8rem !important; transition: all 0.15s !important;
        width: 100% !important;
    }
    .stButton > button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; }

    /* Reset button highlight */
    .reset-btn > button {
        border-color: #ef4444 !important; color: #ef4444 !important;
    }
    .reset-btn > button:hover { background: #1a0a0a !important; }

    /* Debug panel cards */
    .debug-card {
        background: #0f172a; border: 1px solid #1e293b;
        border-radius: 10px; padding: 0.9rem 1rem; margin-bottom: 0.7rem;
    }
    .debug-card h4 {
        margin: 0 0 0.5rem 0; font-size: 0.7rem; font-weight: 600;
        color: #475569; text-transform: uppercase; letter-spacing: 0.08em;
        font-family: 'IBM Plex Mono', monospace;
    }
    .debug-value {
        font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #e2e8f0;
    }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace;
    }
    .badge-blue  { background: #1e3a5f; color: #60a5fa; border: 1px solid #1d4ed8; }
    .badge-green { background: #0f2d1f; color: #34d399; border: 1px solid #059669; }
    .badge-yellow{ background: #2d2000; color: #fbbf24; border: 1px solid #d97706; }
    .badge-gray  { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
    .badge-red   { background: #2d0f0f; color: #f87171; border: 1px solid #dc2626; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #080d1a !important; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] .stMarkdown { color: #94a3b8; }

    /* Global dark bg */
    .stApp { background: #0a0f1e; }
    hr { border-color: #1e293b; }
</style>
""", unsafe_allow_html=True)


INTENT_BADGE = {
    "STATUS_QUERY":   ("badge-blue",   "📦 STATUS_QUERY"),
    "RESCHEDULE":     ("badge-yellow", "📅 RESCHEDULE"),
    "CREATE_TICKET":  ("badge-green",  "🎫 CREATE_TICKET"),
    "GREETING":       ("badge-gray",   "👋 GREETING"),
    "CANCEL":         ("badge-red",    "🚫 CANCEL"),
    "UNKNOWN":        ("badge-gray",   "❓ UNKNOWN"),
}

HANDLER_BADGE = {
    "StatusHandler":    ("badge-blue",   "📦 Status"),
    "TicketHandler":    ("badge-green",  "🎫 Ticket"),
    "RescheduleHandler":("badge-yellow", "📅 Reschedule"),
}


def intent_badge(intent: str) -> str:
    cls, label = INTENT_BADGE.get(intent, ("badge-gray", f"❓ {intent}"))
    return f'<span class="badge {cls}">{label}</span>'


def handler_badge(handler_name: str) -> str:
    if not handler_name:
        return '<span class="badge badge-gray">— ninguno</span>'
    cls, label = HANDLER_BADGE.get(handler_name, ("badge-gray", handler_name))
    return f'<span class="badge {cls}">{label}</span>'


def init_session(client_name: str = None):
    st.session_state.agent = Agent(client_name=client_name)
    st.session_state.messages = []
    st.session_state.last_intent = None
    greeting = st.session_state.agent.chat("")
    st.session_state.messages.append({"role": "bot", "content": greeting})


if "thinking" not in st.session_state:
    st.session_state.thinking = False

# Init state

if "agent" not in st.session_state:
    init_session()
if "selected_client" not in st.session_state:
    st.session_state.selected_client = None
if "last_intent" not in st.session_state:
    st.session_state.last_intent = None


# Layout: sidebar + main + debug panel

sidebar, main_col, debug_col = st.columns([1, 2.8, 1.2])


# SIDEBAR — Configuración
with sidebar:
    st.markdown("### ⚙️ Config")
    st.markdown("---")

    clients     = list_available_clients()
    client_opts = ["(default)"] + clients
    current_idx = 0
    if st.session_state.selected_client in clients:
        current_idx = client_opts.index(st.session_state.selected_client)

    selected = st.selectbox("Cliente", client_opts, index=current_idx)
    client_name = None if selected == "(default)" else selected

    if client_name != st.session_state.selected_client:
        st.session_state.selected_client = client_name
        init_session(client_name)
        st.rerun()

    st.markdown("---")

    if st.button("🔄 Nueva conversación"):
        init_session(st.session_state.selected_client)
        st.rerun()

    st.markdown("---")

    agent  = st.session_state.agent
    config = agent.config
    st.markdown(f"**Cliente:** `{config.get('name', 'LogiBot')}`")
    st.markdown(f"**Tono:** `{config.get('tone', 'formal')}`")
    st.markdown(f"**Idioma:** `{config.get('language', 'es').upper()}`")
    escalate = config.get("policies", {}).get("escalate_after_attempts", "—")
    st.markdown(f"**Escala tras:** `{escalate}` intentos")


# MAIN — Chat

with main_col:
    client_label = st.session_state.selected_client or "default"
    st.markdown(f"""
    <div class="logibot-header">
        <div>
            <h1>🚚 LogiBot</h1>
            <p>Asistente de soporte logístico</p>
        </div>
        <span class="client-badge">{client_label}</span>
    </div>
    """, unsafe_allow_html=True)

    # Chat messages
    html = '<div class="chat-container" id="chat-box">'
    for msg in st.session_state.messages:
        content = msg["content"].replace("<", "&lt;").replace(">", "&gt;")
        if msg["role"] == "user":
            html += f'<div class="msg-user"><div class="bubble">{content}</div></div>'
        else:
            html += f'''<div class="msg-bot">
                <div class="bot-avatar">🤖</div>
                <div class="bubble">{content}</div>
            </div>'''
    
    if st.session_state.thinking:
        html += '''
        <div class="msg-bot">
            <div class="bot-avatar">🤖</div>
            <div class="bubble">
                <div class="typing">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
        '''
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("""
        <script>
        const chat = window.parent.document.querySelector('#chat-box');
        if(chat){
            chat.scrollTop = chat.scrollHeight;
        }
        </script>
        """, unsafe_allow_html=True)

    # Input
    with st.form(key="chat_form", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        with c1:
            user_input = st.text_input(
                "msg",
                placeholder="Escribe tu mensaje aquí...",
                label_visibility="collapsed",
                disabled=st.session_state.thinking
            )
        with c2:
            submitted = st.form_submit_button(
                "Enviar",
                use_container_width=True,
                disabled=st.session_state.thinking
            )

    if st.session_state.thinking and "pending_message" in st.session_state:

        msg = st.session_state.pending_message
        
        from agent.llm import detect_intent

        try:
            detection = detect_intent(msg)
            st.session_state.last_intent = detection.get("intent", "UNKNOWN")
        except Exception:
            st.session_state.last_intent = "UNKNOWN"

        response = st.session_state.agent.chat(msg)

        st.session_state.messages.append({
            "role": "bot",
            "content": response
        })

        st.session_state.thinking = False
        del st.session_state.pending_message

        st.rerun()
    
    if submitted and user_input.strip() and not st.session_state.thinking:
        # mostrar mensaje
        st.session_state.messages.append({
            "role": "user",
            "content": user_input.strip()
        })

        # guardar mensaje para procesarlo luego
        st.session_state.pending_message = user_input.strip()

        # activar estado thinking
        st.session_state.thinking = True

        st.rerun()



# DEBUG PANEL — Estado del agente

with debug_col:
    st.markdown("### 🔍 Debug")
    st.markdown("---")

    agent = st.session_state.agent

    # Intent detectado
    last_intent = st.session_state.get("last_intent")
    st.markdown(f"""
    <div class="debug-card">
        <h4>Último Intent</h4>
        <div class="debug-value">{intent_badge(last_intent) if last_intent else '<span class="badge badge-gray">— esperando</span>'}</div>
    </div>
    """, unsafe_allow_html=True)

    # Handler activo
    handler      = agent.active_handler
    handler_name = type(handler).__name__ if handler else None
    st.markdown(f"""
    <div class="debug-card">
        <h4>Handler Activo</h4>
        <div class="debug-value">{handler_badge(handler_name)}</div>
    </div>
    """, unsafe_allow_html=True)

    # Slots recolectados
    slots = handler.collected if handler else {}
    slots_html = ""
    if slots:
        for k, v in slots.items():
            slots_html += f'<div style="margin:2px 0"><span style="color:#475569;font-size:0.72rem">{k}:</span> <span style="color:#e2e8f0;font-size:0.78rem">{v}</span></div>'
    else:
        slots_html = '<span style="color:#475569;font-size:0.78rem">— sin slots</span>'

    st.markdown(f"""
    <div class="debug-card">
        <h4>Slots Recolectados</h4>
        <div class="debug-value" style="font-family:\'IBM Plex Mono\',monospace">{slots_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Estado del handler
    if handler:
        flags = []
        if getattr(handler, "awaiting_confirmation", False):
            flags.append('<span class="badge badge-yellow">⏳ confirmación</span>')
        if getattr(handler, "awaiting_edit_choice", False):
            flags.append('<span class="badge badge-yellow">✏️ editando</span>')
        if getattr(handler, "_waiting_followup", False):
            flags.append('<span class="badge badge-blue">💬 follow-up</span>')
        if handler.is_done():
            flags.append('<span class="badge badge-gray">✅ done</span>')

        flags_html = " ".join(flags) if flags else '<span class="badge badge-gray">idle</span>'
    else:
        flags_html = '<span class="badge badge-gray">— inactivo</span>'

    st.markdown(f"""
    <div class="debug-card">
        <h4>Estado</h4>
        <div class="debug-value">{flags_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Turnos de conversación
    turns = len([m for m in st.session_state.messages if m["role"] == "user"])
    unknown = agent._unknown_count
    st.markdown(f"""
    <div class="debug-card">
        <h4>Métricas</h4>
        <div class="debug-value">
            <div style="margin:2px 0"><span style="color:#475569;font-size:0.72rem">turnos:</span> <span style="color:#e2e8f0">{turns}</span></div>
            <div style="margin:2px 0"><span style="color:#475569;font-size:0.72rem">unknown count:</span> <span style="color:{'#f87171' if unknown > 0 else '#e2e8f0'}">{unknown}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)