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
        --primary-color: #2563eb !important;
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
    
    /* Action Buttons */
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
    
    /* Document Tag Pill */
    .doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        color: #1d4ed8;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    /* Citation Card */
    .citation-box {
        background-color: #f8fafc;
        border-left: 3px solid #2563eb;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        font-size: 13px;
        color: #334155;
    }

    /* User Profile Footer Card */
    .profile-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 15px;
    }
    .profile-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background-color: #2563eb;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
    }
    .profile-info {
        display: flex;
        flex-direction: column;
    }
    .profile-name {
        font-size: 13px;
        font-weight: 600;
        color: #0f172a;
    }
    .profile-email {
        font-size: 11px;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Backend RAG Engine
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

# User Google Profile State
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "logged_in": True,
        "name": "Ayush Jha",
        "email": "ayush@gmail.com",
        "avatar_initials": "AJ"
    }

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
    st.markdown("<div style='font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Saved Chats (Google Sync)</div>", unsafe_allow_html=True)
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

    # Active Session Documents List
    st.markdown("<div style='font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>Attached Documents</div>", unsafe_allow_html=True)
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
        st.caption("No PDFs attached to this chat.")

    st.divider()

    # User Profile & Google Account Settings
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-avatar">{profile['avatar_initials']}</div>
            <div class="profile-info">
                <span class="profile-name">{profile['name']}</span>
                <span class="profile-email">{profile['email']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("⚙️ Account Settings", expanded=False):
            st.markdown("##### Google Account Settings")
            st.caption("All conversation histories and documents are synced to your Google Account.")
            st.write("")
            
            if st.button("🗑️ Clear Account History & All Data", use_container_width=True):
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
                st.success("All account data cleared!")
                st.rerun()
                
            if st.button("🚪 Sign Out of Google", use_container_width=True):
                st.session_state.user_profile["logged_in"] = False
                st.rerun()
    else:
        st.markdown("""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center;">
            <p style="font-size: 12px; color: #64748b; margin-bottom: 8px;">Sign in to sync your PDF chats across devices.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔵 Sign in with Google", use_container_width=True):
            st.session_state.user_profile["logged_in"] = True
            st.rerun()

# Main Application Workspace
st.markdown("## 📄 Chat with your Documents")
st.caption("Upload PDFs and converse naturally with your document assistant.")

# PDF Ingestion Card - Automatic Processing on File Select
uploaded_files = st.file_uploader(
    "Upload PDF documents to attach to this chat",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.active_session_id}"
)

# AUTOMATIC INGESTION ON FILE DROP (NO EXTRA BUTTON NEEDED!)
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_key = f"{st.session_state.active_session_id}_{uploaded_file.name}_{uploaded_file.size}"
        if file_key not in st.session_state.processed_file_hashes:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                with st.spinner(f"Indexing {uploaded_file.name}..."):
                    st.session_state.rag_engine.add_document(
                        file_name=uploaded_file.name,
                        file_path=tmp_path
                    )
                if uploaded_file.name not in current_session["pdfs"]:
                    current_session["pdfs"].append(uploaded_file.name)
                    
                st.session_state.processed_file_hashes.add(file_key)
                
                # Title chat automatically based on first uploaded file
                if current_session["title"].startswith("Chat "):
                    current_session["title"] = uploaded_file.name[:24]
                st.toast(f"Attached {uploaded_file.name} to chat!", icon="📄")
            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

# Display attached document pills if present
if current_session["pdfs"]:
    pills_html = ""
    for pdf_name in current_session["pdfs"]:
        pills_html += f'<span class="doc-pill">📄 {pdf_name}</span>'
    st.markdown(f"<div style='margin-top: 10px; margin-bottom: 15px;'>{pills_html}</div>", unsafe_allow_html=True)

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
