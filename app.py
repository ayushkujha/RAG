import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from rag_engine import RAGEngine

# Load environment variables from .env file automatically
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="PDF AI Chat Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimalist Light Theme Custom CSS
st.markdown("""
<style>
    /* Force Light Theme Base Variables */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        --background-color: #ffffff !important;
        --secondary-background-color: #f9fafb !important;
        --text-color: #1f2937 !important;
        --primary-color: #4f46e5 !important;
    }
    
    .stApp {
        background-color: #ffffff !important;
        color: #1f2937 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #f9fafb !important;
        border-right: 1px solid #e5e7eb !important;
    }
    
    /* Card Component */
    .stat-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
    }
    .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #4f46e5;
    }
    .stat-label {
        font-size: 12px;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    
    /* Clean button styling */
    div.stButton > button {
        border-radius: 6px !important;
        border: 1px solid #d1d5db !important;
        background-color: #ffffff !important;
        color: #374151 !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #f3f4f6 !important;
        border-color: #cbd5e1 !important;
        color: #111827 !important;
    }
    
    /* Suggestion pills */
    .suggestion-btn button {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        color: #4b5563 !important;
        text-align: left !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        border-radius: 8px !important;
        width: 100% !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
    }
    .suggestion-btn button:hover {
        border-color: #4f46e5 !important;
        color: #4f46e5 !important;
        background-color: #f5f3ff !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG Engine in session state
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []

def reset_suggestions():
    st.session_state.suggested_questions = []

# Fetch active document metrics from ChromaDB
doc_counts = st.session_state.rag_engine.get_indexed_documents()
total_docs = len(doc_counts)
total_chunks = st.session_state.rag_engine.count_chunks()

# Sidebar Layout
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 5px; margin-bottom: 15px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <line x1="10" y1="9" x2="8" y2="9"></line>
        </svg>
        <span style="font-size: 20px; font-weight: 700; color: #111827;">PDF Chat Assistant</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Upload PDFs and converse directly with your documents.")
    st.divider()

    # ChromaDB Statistics Card
    st.markdown("### 📊 Vector Store Metrics")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{total_docs}</div>
            <div class="stat-label">PDFs Indexed</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{total_chunks}</div>
            <div class="stat-label">Chroma Chunks</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Indexed PDF Documents List
    st.markdown("### 🗂️ Indexed Documents")
    if doc_counts:
        for idx, (filename, chunk_count) in enumerate(doc_counts.items()):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"📄 **{filename}**")
                st.caption(f"{chunk_count} vector chunks")
            with col_b:
                if st.button("🗑️", key=f"del_{filename}_{idx}", help=f"Remove {filename} from ChromaDB"):
                    st.session_state.rag_engine.delete_document(filename)
                    reset_suggestions()
                    st.toast(f"Removed {filename} from ChromaDB!", icon="🗑️")
                    st.rerun()
            st.divider()
    else:
        st.info("No PDF documents currently indexed in ChromaDB.")

    st.divider()

    # Export & Reset Utilities
    st.markdown("### ⚙️ Options")
    if st.session_state.chat_history:
        chat_markdown = "# PDF Chat History\n\n"
        for msg in st.session_state.chat_history:
            role_name = "User" if msg["role"] == "user" else "Assistant"
            chat_markdown += f"### {role_name}\n{msg['content']}\n\n"
            
        st.download_button(
            label="📥 Export Chat History",
            data=chat_markdown,
            file_name="pdf_chat_history.md",
            mime="text/markdown",
            use_container_width=True
        )

    if st.button("🗑️ Clear Vector Database", use_container_width=True):
        st.session_state.rag_engine.clear_index()
        st.session_state.chat_history = []
        reset_suggestions()
        st.success("ChromaDB vector store cleared successfully!")
        st.rerun()

# Main Dashboard View
st.title("📄 PDF AI Chat Companion")
st.markdown("Upload your PDF files to index them into ChromaDB and start asking questions with instant page citations.")
st.write("")

# PDF Document Upload Section
with st.expander("📁 PDF Ingestion Panel", expanded=(total_docs == 0)):
    st.markdown("##### Upload PDF files to store in ChromaDB")
    uploaded_files = st.file_uploader(
        "Drag and drop PDF files here",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("🚀 Process & Index PDFs in ChromaDB", use_container_width=True):
            with st.spinner("Extracting text, creating embeddings, and storing in ChromaDB..."):
                newly_added = 0
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        num_chunks = st.session_state.rag_engine.add_document(
                            file_name=uploaded_file.name,
                            file_path=tmp_path
                        )
                        newly_added += 1
                        st.info(f"Indexed **{uploaded_file.name}** ({num_chunks} vector chunks).")
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                
                if newly_added > 0:
                    reset_suggestions()
                    st.success(f"Successfully added {newly_added} document(s) to ChromaDB!")
                    st.rerun()

st.divider()

# Suggested Questions Generator
if total_chunks > 0:
    if not st.session_state.suggested_questions:
        with st.spinner("Generating suggested study questions..."):
            st.session_state.suggested_questions = st.session_state.rag_engine.generate_suggested_questions()
            
    if st.session_state.suggested_questions:
        st.markdown("💡 **Suggested Questions:**")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.suggested_questions):
            with cols[i % 3]:
                st.markdown('<div class="suggestion-btn">', unsafe_allow_html=True)
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.active_prompt = q
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# Chat Area
st.subheader("💬 Chat with your PDF")

# Display previous chat messages
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("🔍 Verified PDF Sources (ChromaDB)"):
                for idx, chunk in enumerate(message["sources"]):
                    src_name = chunk["metadata"].get("source", "PDF")
                    page_num = chunk["metadata"].get("page", 1)
                    similarity = chunk.get("similarity", 0.0)
                    st.markdown(f"**Source {idx+1}:** `{src_name}` (Page {page_num}) — *Match Score: {similarity:.2f}*")
                    st.info(chunk["text"])

# Handle Chat Input
prompt = st.chat_input("Ask a question about your uploaded PDF...")
if "active_prompt" in st.session_state and st.session_state.active_prompt:
    prompt = st.session_state.active_prompt
    st.session_state.active_prompt = None

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Searching ChromaDB & generating response..."):
            try:
                response_text, sources = st.session_state.rag_engine.query_with_context(
                    query=prompt,
                    chat_history=st.session_state.chat_history[:-1]
                )
                message_placeholder.markdown(response_text)
                
                if sources:
                    with st.expander("🔍 Verified PDF Sources (ChromaDB)", expanded=False):
                        for idx, chunk in enumerate(sources):
                            src_name = chunk["metadata"].get("source", "PDF")
                            page_num = chunk["metadata"].get("page", 1)
                            similarity = chunk.get("similarity", 0.0)
                            st.markdown(f"**Source {idx+1}:** `{src_name}` (Page {page_num}) — *Match Score: {similarity:.2f}*")
                            st.info(chunk["text"])
                else:
                    st.caption("No matching PDF context found in ChromaDB.")

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response_text,
                    "sources": sources
                })
            except Exception as e:
                st.error(f"Error querying RAG assistant: {e}")
