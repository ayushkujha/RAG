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
    page_title="DocuChat AI - Chat with PDFs",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Minimalist CSS
st.markdown("""
<style>
    /* Global Theme Overrides */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        --background-color: #ffffff !important;
        --secondary-background-color: #f8fafc !important;
        --text-color: #0f172a !important;
        --primary-color: #3b82f6 !important;
    }
    
    .stApp {
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    
    /* Primary Action Buttons */
    div.stButton > button {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        color: #1e293b !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }
    
    /* Active Session Highlight */
    .chat-history-item {
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        cursor: pointer;
        font-size: 14px;
        color: #334155;
        border: 1px solid transparent;
        transition: background-color 0.15s ease;
    }
    .chat-history-item:hover {
        background-color: #f1f5f9;
    }
    .chat-history-item.active {
        background-color: #eff6ff;
        border-color: #bfdbfe;
        color: #1d4ed8;
        font-weight: 600;
    }

    /* Document Tag Pill */
    .doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        color: #475569;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    /* Clean Citation Card */
    .citation-box {
        background-color: #f8fafc;
        border-left: 3px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        font-size: 13px;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Backend RAG Engine
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

# Initialize Chat Sessions State
if "sessions" not in st.session_state:
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

# Ensure active session exists
if st.session_state.active_session_id not in st.session_state.sessions:
    st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]

current_session = st.session_state.sessions[st.session_state.active_session_id]

# Sidebar
with st.sidebar:
    # Branding Header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 4px; margin-bottom: 16px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <line x1="10" y1="9" x2="8" y2="9"></line>
        </svg>
        <span style="font-size: 20px; font-weight: 700; color: #0f172a; letter-spacing: -0.02em;">DocuChat AI</span>
    </div>
    """, unsafe_allow_html=True)
    
    # New Chat Primary Action Button
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

    # Chat History List
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

    # Active Session Documents
    st.markdown("<div style='font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Documents in Chat</div>", unsafe_allow_html=True)
    if current_session["pdfs"]:
        for pdf_name in current_session["pdfs"]:
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                st.markdown(f"<span style='font-size:13px; color:#334155;'>📄 {pdf_name}</span>", unsafe_allow_html=True)
            with col_d2:
                if st.button("🗑️", key=f"remove_pdf_{pdf_name}"):
                    st.session_state.rag_engine.delete_document(pdf_name)
                    current_session["pdfs"].remove(pdf_name)
                    st.rerun()
    else:
        st.caption("No PDFs attached to this chat yet.")

    st.divider()
    if st.button("🧹 Clear All Data", use_container_width=True):
        st.session_state.rag_engine.clear_index()
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
        st.rerun()

# Main Application Workspace
st.markdown("## 📄 Chat with your Documents")
st.caption("Upload PDFs and converse naturally with your document assistant.")

# PDF Ingestion Card
with st.expander("📁 Attach PDFs to Chat", expanded=(len(current_session["pdfs"]) == 0)):
    uploaded_files = st.file_uploader(
        "Upload PDF files for this conversation",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("Process & Attach Documents", use_container_width=True):
            with st.spinner("Processing document text..."):
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        st.session_state.rag_engine.add_document(
                            file_name=uploaded_file.name,
                            file_path=tmp_path
                        )
                        if uploaded_file.name not in current_session["pdfs"]:
                            current_session["pdfs"].append(uploaded_file.name)
                            
                        # Automatically title the chat based on the first PDF
                        if current_session["title"].startswith("Chat "):
                            current_session["title"] = uploaded_file.name[:24]
                    except Exception as e:
                        st.error(f"Error reading {uploaded_file.name}: {e}")
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                            
                st.toast("Documents attached to conversation!", icon="📄")
                st.rerun()

# Display attached document pills if present
if current_session["pdfs"]:
    pills_html = ""
    for pdf_name in current_session["pdfs"]:
        pills_html += f'<span class="doc-pill">📄 {pdf_name}</span>'
    st.markdown(f"<div style='margin-bottom: 15px;'>{pills_html}</div>", unsafe_allow_html=True)

st.divider()

# Chat Conversation Messages
for message in current_session["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("🔍 Referenced Document Sources", expanded=False):
                for idx, src in enumerate(message["sources"]):
                    doc_name = src["metadata"].get("source", "Document")
                    page_num = src["metadata"].get("page", 1)
                    st.markdown(f"**Source {idx+1}:** `📄 {doc_name}` — *Page {page_num}*")
                    st.markdown(f'<div class="citation-box">{src["text"]}</div>', unsafe_allow_html=True)

# User Chat Input
prompt = st.chat_input("Ask a question about your uploaded PDF documents...")

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
                    with st.expander("🔍 Referenced Document Sources", expanded=False):
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
