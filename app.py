import os
import uuid
import tempfile
import streamlit as st
from dotenv import load_dotenv
from rag_engine import RAGEngine

# Load environment variables automatically
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="DocuChat AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Exact Radial Gradient & #1F2023 Dark Prompt Box Theme
st.markdown("""
<style>
    /* Exact Radial Gradient Canvas from 21st.dev template */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], header[data-testid="stHeader"] {
        background: radial-gradient(125% 125% at 50% 101%, rgba(245,87,2,1) 10.5%, rgba(245,120,2,1) 16%, rgba(245,140,2,1) 17.5%, rgba(245,170,100,1) 25%, rgba(238,174,202,1) 40%, rgba(202,179,214,1) 65%, rgba(148,201,233,1) 100%) !important;
        background-attachment: fixed !important;
        color: #ffffff !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    header[data-testid="stHeader"] {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
        padding-top: 1.5rem !important;
    }
    
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Dark Sidebar */
    [data-testid="stSidebar"] {
        background: #111215 !important;
        border-right: 1px solid #2e3033 !important;
    }
    
    /* Dark Buttons */
    div.stButton > button {
        border-radius: 12px !important;
        border: 1px solid #444444 !important;
        background-color: #1F2023 !important;
        color: #f3f4f6 !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #2E3033 !important;
        border-color: #666666 !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }
    
    /* Floating Hero #1F2023 Prompt Container */
    .prompt-box-card {
        background: #1F2023;
        border: 1px solid #444444;
        border-radius: 24px;
        padding: 35px 30px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
        max-width: 720px;
        margin: 25px auto 20px auto;
        text-align: center;
    }
    
    .hero-title {
        font-size: 34px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin-bottom: 10px;
    }
    .hero-subhead {
        font-size: 15px;
        color: #9CA3AF;
        max-width: 580px;
        margin: 0 auto 20px auto;
        line-height: 1.5;
    }

    /* Interactive Mode Buttons */
    .mode-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        border: 1px solid #444444;
        background-color: #2E3033;
        color: #9CA3AF;
        transition: all 0.2s ease;
    }
    .mode-pill:hover {
        color: #ffffff;
        border-color: #666666;
    }
    .mode-pill.active-search {
        background-color: rgba(30, 174, 219, 0.2);
        border-color: #1EAEDB;
        color: #1EAEDB;
    }
    .mode-pill.active-think {
        background-color: rgba(139, 92, 246, 0.2);
        border-color: #8B5CF6;
        color: #8B5CF6;
    }
    .mode-pill.active-canvas {
        background-color: rgba(249, 115, 22, 0.2);
        border-color: #F97316;
        color: #F97316;
    }

    /* Floating Chat Prompt Input Box */
    div[data-testid="stChatInput"] {
        background-color: #1F2023 !important;
        border: 1px solid #444444 !important;
        border-radius: 24px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #ffffff !important;
    }

    /* Document Tag Pill */
    .doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #1F2023;
        border: 1px solid #444444;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        color: #93c5fd;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    /* Citation Box */
    .citation-box {
        background-color: #1F2023;
        border-left: 3px solid #60a5fa;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        font-size: 13px;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Backend RAG Engine
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

# Auth State
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "logged_in": False,
        "name": "Guest Visitor",
        "email": "visitor@docuchat.ai",
        "avatar_initials": "GV"
    }

# Interactive Modes State
if "active_mode" not in st.session_state:
    st.session_state.active_mode = "standard"  # standard, search, think, canvas

# Chat Sessions State
if "sessions" not in st.session_state:
    initial_id = str(uuid.uuid4())[:8]
    st.session_state.sessions = {
        initial_id: {
            "id": initial_id,
            "title": "New Chat",
            "messages": [],
            "pdfs": []
        }
    }
    st.session_state.active_session_id = initial_id

if "processed_file_hashes" not in st.session_state:
    st.session_state.processed_file_hashes = set()

# Ensure active session exists
if st.session_state.active_session_id not in st.session_state.sessions:
    st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]

current_session = st.session_state.sessions[st.session_state.active_session_id]

# Sidebar
with st.sidebar:
    # Branding Header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 4px; margin-bottom: 16px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <line x1="10" y1="9" x2="8" y2="9"></line>
        </svg>
        <span style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;">DocuChat AI</span>
    </div>
    """, unsafe_allow_html=True)
    
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        new_num = len(st.session_state.sessions) + 1
        st.session_state.sessions[new_id] = {
            "id": new_id,
            "title": f"Chat {new_num}",
            "messages": [],
            "pdfs": []
        }
        st.session_state.active_session_id = new_id
        st.rerun()

    st.divider()

    # Saved Chats History
    st.markdown("<div style='font-size:12px; font-weight:600; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Recent Chats</div>", unsafe_allow_html=True)
    for s_id, s_data in list(st.session_state.sessions.items()):
        is_active = (s_id == st.session_state.active_session_id)
        btn_label = f"💬 {s_data['title']}"
        if is_active:
            btn_label = f"🔹 {s_data['title']}"
            
        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            if st.button(btn_label, key=f"session_btn_{s_id}", use_container_width=True):
                st.session_state.active_session_id = s_id
                st.rerun()
        with col_s2:
            if len(st.session_state.sessions) > 1:
                if st.button("✕", key=f"del_sess_{s_id}", help="Delete chat"):
                    del st.session_state.sessions[s_id]
                    if st.session_state.active_session_id == s_id:
                        st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]
                    st.rerun()

    st.divider()

    # Attached Documents List
    st.markdown("<div style='font-size:12px; font-weight:600; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Attached Documents</div>", unsafe_allow_html=True)
    if current_session["pdfs"]:
        for doc_name in current_session["pdfs"]:
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                st.markdown(f"<span style='font-size:13px; color:#cbd5e1;'>📄 {doc_name}</span>", unsafe_allow_html=True)
            with col_d2:
                if st.button("🗑️", key=f"remove_pdf_{doc_name}"):
                    st.session_state.rag_engine.delete_document(doc_name)
                    current_session["pdfs"].remove(doc_name)
                    st.rerun()
    else:
        st.caption("No documents attached yet.")

    st.divider()

    # User Profile / Account Footer
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"""
        <div style="background-color: #1F2023; border: 1px solid #444444; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
            <div style="font-size: 13px; font-weight: 600; color: #ffffff;">👤 {profile['name']}</div>
            <div style="font-size: 11px; color: #94a3b8;">{profile['email']}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("⚙️ Account Settings", expanded=False):
            if st.button("🗑️ Clear My Saved Data", use_container_width=True):
                st.session_state.rag_engine.clear_index()
                st.session_state.processed_file_hashes.clear()
                initial_id = str(uuid.uuid4())[:8]
                st.session_state.sessions = {
                    initial_id: {
                        "id": initial_id,
                        "title": "Chat 1",
                        "messages": [],
                        "pdfs": []
                    }
                }
                st.session_state.active_session_id = initial_id
                st.success("Account data cleared!")
                st.rerun()
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state.user_profile["logged_in"] = False
                st.rerun()
    else:
        if st.button("🔵 Sign In with Google", use_container_width=True):
            st.session_state.user_profile["logged_in"] = True
            st.session_state.user_profile["name"] = "Ayush Jha"
            st.session_state.user_profile["email"] = "ayush@gmail.com"
            st.rerun()

# Top Navigation Bar
col_nav1, col_nav2 = st.columns([4, 1])
with col_nav1:
    st.markdown("<span style='font-size: 22px; font-weight: 800; color: #ffffff; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>📄 DocuChat AI</span>", unsafe_allow_html=True)
with col_nav2:
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"<div style='text-align: right;'><span style='font-size: 13px; background-color: #1F2023; border: 1px solid #444444; padding: 6px 14px; border-radius: 20px; color: #ffffff;'>👤 {profile['name']}</span></div>", unsafe_allow_html=True)
    else:
        if st.button("Sign In / Visitor Mode", key="top_signin"):
            st.session_state.user_profile["logged_in"] = True
            st.session_state.user_profile["name"] = "Ayush Jha"
            st.session_state.user_profile["email"] = "ayush@gmail.com"
            st.rerun()

st.write("")

# Document Attachment Bar with embedded (+) file selection
with st.expander("📎 Attach Documents (+)", expanded=(len(current_session["pdfs"]) == 0)):
    uploaded_files = st.file_uploader(
        "Upload PDF, Word (.docx), Excel (.xlsx), CSV, or Text files to chat",
        type=["pdf", "docx", "csv", "xlsx", "txt", "md"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.active_session_id}"
    )

    # AUTOMATIC INGESTION ON FILE DROP
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_key = f"{st.session_state.active_session_id}_{uploaded_file.name}_{uploaded_file.size}"
            if file_key not in st.session_state.processed_file_hashes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    with st.spinner(f"Reading {uploaded_file.name}..."):
                        st.session_state.rag_engine.add_document(
                            file_name=uploaded_file.name,
                            file_path=tmp_path
                        )
                    if uploaded_file.name not in current_session["pdfs"]:
                        current_session["pdfs"].append(uploaded_file.name)
                        
                    st.session_state.processed_file_hashes.add(file_key)
                    if current_session["title"] in ["New Chat", "Chat 1", "Chat 2"]:
                        current_session["title"] = uploaded_file.name[:24]
                    st.toast(f"Attached {uploaded_file.name}!", icon="📄")
                except Exception as e:
                    st.error(f"Error reading {uploaded_file.name}: {e}")
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

# Attached document pills
if current_session["pdfs"]:
    pills_html = ""
    for doc_name in current_session["pdfs"]:
        pills_html += f'<span class="doc-pill">📄 {doc_name}</span>'
    st.markdown(f"<div style='margin-bottom: 15px;'>{pills_html}</div>", unsafe_allow_html=True)

# Mode Selector Row
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    if st.button("🌐 Web Search", use_container_width=True):
        st.session_state.active_mode = "search" if st.session_state.active_mode != "search" else "standard"
        st.rerun()
with col_m2:
    if st.button("🧠 Think Deeply", use_container_width=True):
        st.session_state.active_mode = "think" if st.session_state.active_mode != "think" else "standard"
        st.rerun()
with col_m3:
    if st.button("📁 Canvas Mode", use_container_width=True):
        st.session_state.active_mode = "canvas" if st.session_state.active_mode != "canvas" else "standard"
        st.rerun()
with col_m4:
    if st.button("🎙️ Voice Note", use_container_width=True):
        st.session_state.active_mode = "voice" if st.session_state.active_mode != "voice" else "standard"
        st.rerun()

# Centered Hero View over Exact Radial Gradient Canvas (if no messages yet)
if len(current_session["messages"]) == 0:
    mode_desc = "Standard Mode"
    if st.session_state.active_mode == "search":
        mode_desc = "🌐 Web Search Mode Active"
    elif st.session_state.active_mode == "think":
        mode_desc = "🧠 Think Deeply Mode Active"
    elif st.session_state.active_mode == "canvas":
        mode_desc = "📁 Canvas Creation Mode Active"
    elif st.session_state.active_mode == "voice":
        mode_desc = "🎙️ Voice Recording Mode Active"

    st.markdown(f"""
    <div class="prompt-box-card">
        <div class="hero-title">Type your message here...</div>
        <div class="hero-subhead">Attach any PDF, Word, Excel, CSV, or Text document above. ({mode_desc})</div>
        <div style="display: flex; justify-content: center; gap: 20px; color: #ffffff; font-size: 22px;">
            <span title="Attach Document">📎</span>
            <span title="Web Search">🌐</span>
            <span title="Think Deeply">🧠</span>
            <span title="Canvas Mode">📁</span>
            <span title="Voice Note">🎙️</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Active Chat Conversation Messages
for message in current_session["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("🔍 Document Citations", expanded=False):
                for idx, src in enumerate(message["sources"]):
                    doc_name = src["metadata"].get("source", "Document")
                    page_num = src["metadata"].get("page", 1)
                    st.markdown(f"**Source {idx+1}:** `📄 {doc_name}` — *Page {page_num}*")
                    st.markdown(f'<div class="citation-box">{src["text"]}</div>', unsafe_allow_html=True)

# Fixed Floating Prompt Input Box
placeholder_text = "Type your message here..."
if st.session_state.active_mode == "search":
    placeholder_text = "Search the web..."
elif st.session_state.active_mode == "think":
    placeholder_text = "Think deeply..."
elif st.session_state.active_mode == "canvas":
    placeholder_text = "Create on canvas..."

prompt = st.chat_input(placeholder_text)

if prompt:
    formatted_prompt = prompt
    if st.session_state.active_mode != "standard":
        formatted_prompt = f"[{st.session_state.active_mode.capitalize()} Mode] {prompt}"

    with st.chat_message("user"):
        st.markdown(formatted_prompt)
    current_session["messages"].append({"role": "user", "content": formatted_prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Analyzing document context..."):
            try:
                response_text, sources = st.session_state.rag_engine.query_with_context(
                    query=formatted_prompt,
                    chat_history=current_session["messages"][:-1]
                )
                message_placeholder.markdown(response_text)
                
                if sources:
                    with st.expander("🔍 Document Citations", expanded=False):
                        for idx, src in enumerate(sources):
                            doc_name = src["metadata"].get("source", "Document")
                            page_num = src["metadata"].get("page", 1)
                            st.markdown(f"**Source {idx+1}:** `📄 {doc_name}` — *Page {page_num}*")
                            st.markdown(f'<div class="citation-box">{src["text"]}</div>', unsafe_allow_html=True)

                current_session["messages"].append({
                    "role": "assistant",
                    "content": response_text,
                    "sources": sources
                })
            except Exception as e:
                st.error(f"Unable to process query: {e}")
