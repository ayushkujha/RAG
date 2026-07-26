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

# Premium Minimalist Dark Theme Custom CSS
st.markdown("""
<style>
    /* Dark Theme Core Variables */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        --background-color: #0b0f19 !important;
        --secondary-background-color: #111827 !important;
        --text-color: #f8fafc !important;
        --primary-color: #3b82f6 !important;
    }
    
    .stApp {
        background-color: #0b0f19 !important;
        color: #f8fafc !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1f2937 !important;
    }
    
    /* Top Navbar */
    .top-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0 20px 0;
        border-bottom: 1px solid #1f2937;
        margin-bottom: 30px;
    }
    
    /* Button Styling */
    div.stButton > button {
        border-radius: 8px !important;
        border: 1px solid #374151 !important;
        background-color: #1f2937 !important;
        color: #f3f4f6 !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #374151 !important;
        border-color: #4b5563 !important;
        color: #ffffff !important;
    }
    
    /* Document Tag Pill */
    .doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        color: #60a5fa;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    /* Citation Box */
    .citation-box {
        background-color: #1e293b;
        border-left: 3px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        font-size: 13px;
        color: #cbd5e1;
    }

    /* Centered Hero Header */
    .hero-container {
        text-align: center;
        margin-top: 40px;
        margin-bottom: 30px;
    }
    .hero-title {
        font-size: 36px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin-bottom: 10px;
    }
    .hero-subhead {
        font-size: 16px;
        color: #94a3b8;
        max-width: 600px;
        margin: 0 auto;
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
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
    st.markdown("<div style='font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Recent Chats</div>", unsafe_allow_html=True)
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
    st.markdown("<div style='font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Attached Documents</div>", unsafe_allow_html=True)
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
        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
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
    st.markdown("<span style='font-size: 18px; font-weight: 600; color: #f8fafc;'>📄 DocuChat AI</span>", unsafe_allow_html=True)
with col_nav2:
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"<div style='text-align: right;'><span style='font-size: 13px; background-color: #1e293b; border: 1px solid #334155; padding: 6px 12px; border-radius: 20px; color: #60a5fa;'>👤 {profile['name']}</span></div>", unsafe_allow_html=True)
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

# Centered Landing View (if no messages yet in active chat)
if len(current_session["messages"]) == 0:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">What would you like to analyze today?</div>
        <div class="hero-subhead">Attach any PDF, Word, Excel, CSV, or Text document above and type your question below.</div>
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

# Fixed Prompt Input Bar
prompt = st.chat_input("Ask a question about your documents...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    current_session["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Analyzing document context..."):
            try:
                response_text, sources = st.session_state.rag_engine.query_with_context(
                    query=prompt,
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
