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
    page_title="DocuChat AI - Chat with documents, smarter",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Modern UI System CSS (Matching Mockup Design)
st.markdown("""
<style>
    /* Soft Pastel Gradient Canvas */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], header[data-testid="stHeader"] {
        background: linear-gradient(180deg, #F8FAFF 0%, #E9D5FF 35%, #FFD6E8 70%, #FFE3C2 100%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
        padding-top: 1rem !important;
        max-width: 960px !important;
    }
    
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Clean White Glass Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.88) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(226, 232, 240, 0.8) !important;
    }
    
    /* Primary Accent Buttons (Purple Pill) */
    div.stButton > button {
        border-radius: 12px !important;
        border: none !important;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
        transform: translateY(-1.5px) !important;
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.4) !important;
        color: #ffffff !important;
    }
    
    /* White Glass Cards */
    .white-glass-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.8);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.04);
        margin-bottom: 24px;
    }
    
    /* Hero Typography */
    .hero-greeting {
        font-size: 16px;
        font-weight: 600;
        color: #6366f1;
        text-align: center;
        margin-bottom: 6px;
    }
    .hero-heading {
        font-size: 38px;
        font-weight: 800;
        color: #0f172a;
        text-align: center;
        letter-spacing: -0.03em;
        margin-bottom: 8px;
    }
    .hero-subhead {
        font-size: 16px;
        color: #475569;
        text-align: center;
        margin-bottom: 32px;
    }

    /* Document Tag Pill */
    .doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        color: #4f46e5;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    
    /* Citation Box */
    .citation-box {
        background-color: #ffffff;
        border-left: 3px solid #6366f1;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-top: 8px;
        font-size: 13px;
        color: #334155;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    /* Security Note Footer */
    .security-note {
        text-align: center;
        font-size: 13px;
        color: #64748b;
        margin-top: 36px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }

    /* Chat Input Styling */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #0f172a !important;
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

if "preset_prompt" not in st.session_state:
    st.session_state.preset_prompt = ""

# Ensure active session exists
if st.session_state.active_session_id not in st.session_state.sessions:
    st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]

current_session = st.session_state.sessions[st.session_state.active_session_id]

# Sidebar Navigation (Clean White Glass)
with st.sidebar:
    # Branding Header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 4px; margin-bottom: 24px;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <line x1="10" y1="9" x2="8" y2="9"></line>
        </svg>
        <span style="font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">DocuChat AI</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation Items
    st.markdown("<div style='font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px;'>Navigation</div>", unsafe_allow_html=True)
    
    if st.button("🏠 Home", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.sessions[new_id] = {
            "id": new_id,
            "title": "New Chat",
            "messages": [],
            "pdfs": []
        }
        st.session_state.active_session_id = new_id
        st.rerun()

    # Recent Chats History
    st.divider()
    st.markdown("<div style='font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px;'>💬 Recent Chats</div>", unsafe_allow_html=True)
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

    # Attached Documents List
    st.divider()
    st.markdown("<div style='font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px;'>📁 Documents in Chat</div>", unsafe_allow_html=True)
    if current_session["pdfs"]:
        for doc_name in current_session["pdfs"]:
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                st.markdown(f"<span style='font-size:13px; color:#334155; font-weight:500;'>📄 {doc_name}</span>", unsafe_allow_html=True)
            with col_d2:
                if st.button("🗑️", key=f"remove_pdf_{doc_name}"):
                    st.session_state.rag_engine.delete_document(doc_name)
                    current_session["pdfs"].remove(doc_name)
                    st.rerun()
    else:
        st.caption("No documents attached yet.")

    st.divider()

    # User Account Footer
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size: 13px; font-weight: 700; color: #0f172a;">👤 {profile['name']}</div>
            <div style="font-size: 11px; color: #64748b;">{profile['email']}</div>
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
                        "title": "New Chat",
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

# Top Navbar
col_nav1, col_nav2 = st.columns([4, 1])
with col_nav1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">DocuChat AI</span>
    </div>
    """, unsafe_allow_html=True)
with col_nav2:
    profile = st.session_state.user_profile
    if profile["logged_in"]:
        st.markdown(f"<div style='text-align: right;'><span style='font-size: 13px; background-color: #ffffff; border: 1px solid #e2e8f0; padding: 6px 16px; border-radius: 20px; color: #4f46e5; font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,0.04);'>👤 {profile['name']}</span></div>", unsafe_allow_html=True)
    else:
        if st.button("👤 Sign in / Sign up", key="top_signin"):
            st.session_state.user_profile["logged_in"] = True
            st.session_state.user_profile["name"] = "Ayush Jha"
            st.session_state.user_profile["email"] = "ayush@gmail.com"
            st.rerun()

st.write("")

# Hero Header (when starting a conversation)
if len(current_session["messages"]) == 0:
    st.markdown("""
    <div>
        <div class="hero-greeting">👋 Hello there!</div>
        <div class="hero-heading">Chat with your documents, smarter.</div>
        <div class="hero-subhead">Upload your PDF, Word, Excel, CSV or text document and start asking.</div>
    </div>
    """, unsafe_allow_html=True)

# 3. Hero Upload Card (Matching Mockup)
with st.container():
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 20px; padding: 20px 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); margin-bottom: 24px;">
        <div style="font-weight: 700; font-size: 15px; color: #0f172a; margin-bottom: 4px;">📄 Upload Document</div>
        <div style="font-size: 12px; color: #64748b; margin-bottom: 12px;">PDF, DOCX, XLSX, CSV, TXT (Max 100MB)</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drag & Drop files here or browse from computer",
        type=["pdf", "docx", "csv", "xlsx", "txt", "md"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.active_session_id}"
    )

    # Automatic Ingestion
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_key = f"{st.session_state.active_session_id}_{uploaded_file.name}_{uploaded_file.size}"
            if file_key not in st.session_state.processed_file_hashes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    with st.spinner(f"Processing {uploaded_file.name}..."):
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
    st.markdown(f"<div style='margin-bottom: 20px;'>{pills_html}</div>", unsafe_allow_html=True)

# 4. Quick Action Chips (Matching Mockup)
st.markdown("<div style='font-size:14px; font-weight:700; color:#334155; margin-bottom:12px;'>⚡ Quick Actions</div>", unsafe_allow_html=True)
col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
with col_q1:
    if st.button("📊 Ask Question", use_container_width=True):
        st.session_state.preset_prompt = "What is the main topic discussed in the uploaded documents?"
with col_q2:
    if st.button("📜 Summarize", use_container_width=True):
        st.session_state.preset_prompt = "Provide a comprehensive summary of the uploaded documents."
with col_q3:
    if st.button("💡 Explain", use_container_width=True):
        st.session_state.preset_prompt = "Explain the key concepts and ideas from the uploaded documents in simple terms."
with col_q4:
    if st.button("🔀 Compare", use_container_width=True):
        st.session_state.preset_prompt = "Compare the key themes and findings across the uploaded documents."
with col_q5:
    if st.button("📊 Extract Data", use_container_width=True):
        st.session_state.preset_prompt = "Extract all key data, numbers, and important points from the uploaded documents."

st.write("")

# Conversation View
for message in current_session["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("🔍 Document Sources & Citations", expanded=False):
                for idx, src in enumerate(message["sources"]):
                    doc_name = src["metadata"].get("source", "Document")
                    page_num = src["metadata"].get("page", 1)
                    st.markdown(f"**Source {idx+1}:** `📄 {doc_name}` — *Page {page_num}*")
                    st.markdown(f'<div class="citation-box">{src["text"]}</div>', unsafe_allow_html=True)

# 12. Suggested Prompts ("Try asking")
if len(current_session["messages"]) == 0:
    st.markdown("<div style='font-size:14px; font-weight:700; color:#334155; margin-top: 24px; margin-bottom:12px;'>💡 Try asking</div>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        if st.button("Summarize this document", use_container_width=True):
            st.session_state.preset_prompt = "Summarize this document"
    with col_t2:
        if st.button("List the key points", use_container_width=True):
            st.session_state.preset_prompt = "List the key points"
    with col_t3:
        if st.button("Compare the data", use_container_width=True):
            st.session_state.preset_prompt = "Compare the data"
    with col_t4:
        if st.button("Extract important details", use_container_width=True):
            st.session_state.preset_prompt = "Extract important details"

st.write("")

# Unified Single Prompt Input Bar
input_placeholder = "Ask anything about your document. Press Enter to send..."
if st.session_state.preset_prompt:
    prompt = st.chat_input(input_placeholder, key="chat_input_preset")
    # Auto-fill preset prompt logic
    preset_val = st.session_state.preset_prompt
    st.session_state.preset_prompt = ""
    if not prompt:
        prompt = preset_val
else:
    prompt = st.chat_input(input_placeholder)

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
                    with st.expander("🔍 Document Sources & Citations", expanded=False):
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

# Security Footer Note (Matching Mockup)
st.markdown("""
<div class="security-note">
    <span>🛡️</span>
    <span>Your documents are secure and private. We never store your data.</span>
</div>
""", unsafe_allow_html=True)
