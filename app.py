import os
import tempfile
import streamlit as st
from rag_engine import RAGEngine

# Custom layout and title
st.set_page_config(
    page_title="RAG Navigator - Intelligent Doc Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    /* Custom style injection for a modern look */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a24 100%);
    }
    .metric-card {
        background-color: #1e2530;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2e3748;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #4f8bf9;
    }
    .metric-label {
        font-size: 14px;
        color: #8f9cae;
    }
    /* Smooth transition for buttons */
    div.stButton > button {
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 10px rgba(79, 139, 249, 0.3);
        transform: translateY(-1px);
    }
    /* Style suggested questions buttons */
    .suggestion-btn button {
        background-color: #1e2530 !important;
        border: 1px solid #4f8bf9 !important;
        color: #4f8bf9 !important;
        text-align: left !important;
        padding: 8px 12px !important;
        font-size: 14px !important;
        margin-bottom: 5px !important;
        width: 100% !important;
    }
    .suggestion-btn button:hover {
        background-color: #4f8bf9 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")

if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine(api_key=st.session_state.api_key)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "uploaded_files_list" not in st.session_state:
    docs = st.session_state.rag_engine.documents
    unique_sources = list(set([doc["metadata"]["source"] for doc in docs]))
    st.session_state.uploaded_files_list = unique_sources

if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []

# Trigger regeneration of suggested questions
def reset_suggestions():
    st.session_state.suggested_questions = []

# Sidebar Setup
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=70)
    st.title("RAG Settings")
    st.markdown("Configure your Retrieval-Augmented Generation parameters.")
    
    st.divider()
    
    # API Credentials Setup
    api_key_input = st.text_input(
        "Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="Input your Google Gemini API Key here. If empty, the app will attempt to load it from the environmental GEMINI_API_KEY."
    )
    
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        st.session_state.rag_engine.set_api_key(api_key_input)
        reset_suggestions()
        st.success("API key updated successfully!")

    st.divider()

    # RAG Parameters
    st.subheader("Retrieval & Search Settings")
    chunk_size = st.slider("Chunk Size (characters)", min_value=100, max_value=2000, value=1000, step=50)
    chunk_overlap = st.slider("Chunk Overlap (characters)", min_value=0, max_value=500, value=200, step=10)
    top_k = st.slider("Retrieval Count (Top K)", min_value=1, max_value=10, value=5)
    min_similarity = st.slider("Min Similarity Score", min_value=0.0, max_value=1.0, value=0.25, step=0.05)
    
    # Hybrid Search Weight Control
    hybrid_alpha = st.slider(
        "Hybrid Search Weight (Alpha)", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.7, 
        step=0.05,
        help="1.0 = Pure Vector Search (embeddings). 0.0 = Pure Keyword Match. 0.7 = Blended (Recommended)."
    )

    st.divider()
    
    # Export Chat Utility
    st.subheader("Chat Operations")
    if st.session_state.chat_history:
        # Convert chat history to markdown string
        chat_markdown = "# RAG Chat History\n\n"
        for msg in st.session_state.chat_history:
            role_name = "User" if msg["role"] == "user" else "Assistant"
            chat_markdown += f"### {role_name}\n{msg['content']}\n\n"
            
        st.download_button(
            label="📥 Export Chat to Markdown",
            data=chat_markdown,
            file_name="rag_chat_history.md",
            mime="text/markdown",
            use_container_width=True
        )

    # Database Actions
    if st.button("🗑️ Clear Entire Index", use_container_width=True):
        st.session_state.rag_engine.clear_index()
        st.session_state.uploaded_files_list = []
        st.session_state.chat_history = []
        reset_suggestions()
        st.success("Database cleared successfully!")
        st.rerun()

# Main Dashboard layout
st.title("🤖 RAG Navigator")
st.markdown("Upload documents and converse with an AI companion that leverages your indexed files for factual accuracy.")

# Stats Section
cols = st.columns(3)
total_docs = len(st.session_state.uploaded_files_list)
total_chunks = len(st.session_state.rag_engine.documents)
api_status_val = "🟢 Connected" if st.session_state.api_key or os.environ.get("GEMINI_API_KEY") else "🔴 Disconnected"

with cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_docs}</div>
        <div class="metric-label">Documents Indexed</div>
    </div>
    """, unsafe_allow_html=True)
with cols[1]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_chunks}</div>
        <div class="metric-label">Total Text Chunks</div>
    </div>
    """, unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{api_status_val}</div>
        <div class="metric-label">Gemini API Status</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Document Upload & Ingestion Section
with st.expander("📁 Document Ingestion Panel", expanded=(total_docs == 0)):
    st.markdown("### Upload new documents to vector store")
    uploaded_files = st.file_uploader(
        "Select PDF, TXT or Markdown files",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("Process & Embed Documents"):
            with st.spinner("Processing documents, generating embeddings and indexing chunks..."):
                newly_added = 0
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        num_chunks = st.session_state.rag_engine.add_document(
                            file_name=uploaded_file.name,
                            file_path=tmp_path,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap
                        )
                        newly_added += 1
                        st.info(f"Parsed '{uploaded_file.name}' into {num_chunks} chunks.")
                    except Exception as e:
                        st.error(f"Error parsing {uploaded_file.name}: {e}")
                    finally:
                        try:
                            os.remove(tmp_path)
                        except:
                            pass
                
                if newly_added > 0:
                    docs = st.session_state.rag_engine.documents
                    unique_sources = list(set([doc["metadata"]["source"] for doc in docs]))
                    st.session_state.uploaded_files_list = unique_sources
                    reset_suggestions()
                    st.success(f"Successfully processed {newly_added} documents!")
                    st.rerun()

# Document File Manager panel
if st.session_state.uploaded_files_list:
    with st.expander("🗂️ Document File Manager", expanded=False):
        st.markdown("### Manage Indexed Documents")
        
        # Calculate statistics per file
        docs = st.session_state.rag_engine.documents
        for idx, filename in enumerate(st.session_state.uploaded_files_list):
            file_chunks = [d for d in docs if d["metadata"]["source"] == filename]
            chunk_count = len(file_chunks)
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"📄 **{filename}**")
            with col2:
                st.caption(f"{chunk_count} chunks")
            with col3:
                if st.button("🗑️ Delete", key=f"del_{filename}_{idx}", use_container_width=True):
                    removed = st.session_state.rag_engine.delete_document(filename)
                    docs = st.session_state.rag_engine.documents
                    st.session_state.uploaded_files_list = list(set([doc["metadata"]["source"] for doc in docs]))
                    reset_suggestions()
                    st.success(f"Removed {filename} ({removed} chunks) from vector store.")
                    st.rerun()
            st.divider()

st.divider()

# AI Suggested Questions Generator
if total_chunks > 0 and st.session_state.api_key:
    if not st.session_state.suggested_questions:
        with st.spinner("Generating suggested questions based on your files..."):
            st.session_state.suggested_questions = st.session_state.rag_engine.generate_suggested_questions()
            
    if st.session_state.suggested_questions:
        st.markdown("💡 **Suggested Questions:**")
        cols = st.columns(3)
        for i, q in enumerate(st.session_state.suggested_questions):
            with cols[i % 3]:
                st.markdown(f'<div class="suggestion-btn">', unsafe_allow_html=True)
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    # Set the prompt to this question in query execution
                    st.session_state.active_prompt = q
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# Chat Area
st.subheader("💬 Chat with Documents")

# Display previous chat messages
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("🔍 Citations & Sources"):
                for idx, chunk in enumerate(message["sources"]):
                    st.markdown(
                        f"**Source {idx+1}:** `{chunk['metadata']['source']}` (Page {chunk['metadata']['page']}) - "
                        f"*Cosine: {chunk['similarity']:.2f}* | *Keyword Match: {chunk['keyword_score']:.2f}* | *Blended: {chunk['hybrid_score']:.2f}*"
                    )
                    st.info(chunk["text"])

# Handle auto-triggered suggested question click or direct user input
prompt = st.chat_input("Ask a question about your documents...")
if "active_prompt" in st.session_state and st.session_state.active_prompt:
    prompt = st.session_state.active_prompt
    st.session_state.active_prompt = None  # consume the prompt

if prompt:
    if not st.session_state.api_key and not os.environ.get("GEMINI_API_KEY"):
        st.error("Please enter a Gemini API Key in the sidebar configuration to begin chatting.")
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Process response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing documents & generating response..."):
                try:
                    response, sources = st.session_state.rag_engine.query_with_context(
                        query=prompt,
                        chat_history=st.session_state.chat_history[:-1],
                        top_k=top_k,
                        min_similarity=min_similarity,
                        hybrid_alpha=hybrid_alpha
                    )
                    message_placeholder.markdown(response)
                    
                    if sources:
                        with st.expander("🔍 Citations & Sources", expanded=False):
                            for idx, chunk in enumerate(sources):
                                st.markdown(
                                    f"**Source {idx+1}:** `{chunk['metadata']['source']}` (Page {chunk['metadata']['page']}) - "
                                    f"*Cosine: {chunk['similarity']:.2f}* | *Keyword Match: {chunk['keyword_score']:.2f}* | *Blended: {chunk['hybrid_score']:.2f}*"
                                )
                                st.info(chunk["text"])
                    else:
                        st.caption("No matching document chunks found in database.")
                        
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })
                except Exception as e:
                    st.error(f"Error executing query: {e}")
