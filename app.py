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
    /* Force Light Theme CSS Variables at all levels */
    :root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stForm"], [data-testid="stExpander"] {
        --background-color: #ffffff !important;
        --secondary-background-color: #f9fafb !important;
        --text-color: #1f2937 !important;
        --primary-color: #4f46e5 !important;
        
        --st-background-color: #ffffff !important;
        --st-secondary-background-color: #f9fafb !important;
        --st-text-color: #1f2937 !important;
        --st-primary-color: #4f46e5 !important;
    }
    
    /* Base app background */
    .stApp {
        background-color: #ffffff !important;
        color: #1f2937 !important;
    }
    
    /* Sidebar background and border */
    [data-testid="stSidebar"] {
        background-color: #f9fafb !important;
        border-right: 1px solid #e5e7eb !important;
    }
    
    /* Ensure all sidebar text elements are dark gray */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4, 
    [data-testid="stSidebar"] h5, 
    [data-testid="stSidebar"] h6, 
    [data-testid="stSidebar"] small {
        color: #1f2937 !important;
    }
    
    /* Force inputs to be white background with dark text */
    input[type="text"], input[type="password"], textarea {
        background-color: #ffffff !important;
        color: #1f2937 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
    }
    
    /* Focus styles for inputs */
    input[type="text"]:focus, input[type="password"]:focus, textarea:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 1px #4f46e5 !important;
    }
    
    /* Form container styles */
    [data-testid="stForm"] {
        background-color: #ffffff !important;
        border: none !important;
        padding: 0px !important;
    }
    
    /* Expander styling */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
    }
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #1f2937 !important;
        border-bottom: none !important;
    }
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        color: #1f2937 !important;
    }
    
    /* BaseWeb Slider styling to make tracks visible and labels dark */
    div[data-baseweb="slider"] {
        background-color: transparent !important;
    }
    div[data-baseweb="slider"] * {
        color: #1f2937 !important;
    }
    /* Slider track background bar */
    div[data-baseweb="slider"] [role="presentation"] {
        background-color: #e5e7eb !important;
    }
    
    /* Premium Minimalist Card styling */
    .metric-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #111827 !important;
    }
    .metric-label {
        font-size: 13px;
        color: #6b7280 !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    
    /* Standard Button styling */
    div.stButton > button {
        border-radius: 6px !important;
        border: 1px solid #d1d5db !important;
        background-color: #ffffff !important;
        color: #374151 !important;
        font-weight: 500 !important;
        padding: 6px 16px !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #f9fafb !important;
        border-color: #cbd5e1 !important;
        color: #111827 !important;
    }
    
    /* Style suggested questions buttons as outline badge pills */
    .suggestion-btn button {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        color: #4b5563 !important;
        text-align: left !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        margin-bottom: 8px !important;
        width: 100% !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        white-space: normal !important;
        display: block !important;
        line-height: 1.4 !important;
    }
    .suggestion-btn button:hover {
        background-color: #f9fafb !important;
        border-color: #cbd5e1 !important;
        color: #1f2937 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
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

# Initialize configuration parameters in session state
if "chunk_size" not in st.session_state:
    st.session_state.chunk_size = 1000

if "chunk_overlap" not in st.session_state:
    st.session_state.chunk_overlap = 200

if "top_k" not in st.session_state:
    st.session_state.top_k = 5

if "min_similarity" not in st.session_state:
    st.session_state.min_similarity = 0.25

if "hybrid_alpha" not in st.session_state:
    st.session_state.hybrid_alpha = 0.7

# Trigger regeneration of suggested questions
def reset_suggestions():
    st.session_state.suggested_questions = []

# Sidebar Setup
with st.sidebar:
    # Minimalist Logo & Title
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 10px; margin-bottom: 20px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <line x1="10" y1="9" x2="8" y2="9"></line>
        </svg>
        <span style="font-size: 20px; font-weight: 600; color: #111827; letter-spacing: -0.02em;">RAG Navigator</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("A clean, minimalist workspace for document exploration.")
    
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

    # RAG parameters inside a clean form to prevent laggy page reruns
    with st.expander("⚙️ Configuration Options", expanded=False):
        with st.form("settings_form"):
            st.markdown("##### Ingestion Settings")
            st.caption("Applied when uploading new files")
            chunk_size_val = st.slider(
                "Chunk Size (chars)", 
                min_value=100, 
                max_value=2000, 
                value=st.session_state.chunk_size, 
                step=50,
                help="The size of text segments processed at once."
            )
            chunk_overlap_val = st.slider(
                "Chunk Overlap (chars)", 
                min_value=0, 
                max_value=500, 
                value=st.session_state.chunk_overlap, 
                step=10,
                help="Overlapping characters between chunks to preserve context boundaries."
            )
            
            st.divider()
            
            st.markdown("##### Retrieval & Search Settings")
            st.caption("Applied to search queries")
            top_k_val = st.slider(
                "Retrieval Count (Top K)", 
                min_value=1, 
                max_value=10, 
                value=st.session_state.top_k,
                help="Maximum number of relevant chunks to send to the LLM."
            )
            min_similarity_val = st.slider(
                "Min Similarity Score", 
                min_value=0.0, 
                max_value=1.0, 
                value=st.session_state.min_similarity, 
                step=0.05,
                help="Minimum relevance score threshold for retrieved snippets."
            )
            
            # Hybrid Search Weight Control
            hybrid_alpha_val = st.slider(
                "Hybrid Weight (Alpha)", 
                min_value=0.0, 
                max_value=1.0, 
                value=st.session_state.hybrid_alpha, 
                step=0.05,
                help="1.0 = Pure Semantic/Vector Search. 0.0 = Pure Exact Keyword Match. 0.7 = Blended (Recommended)."
            )
            
            if st.form_submit_button("Save & Apply Settings", use_container_width=True):
                st.session_state.chunk_size = chunk_size_val
                st.session_state.chunk_overlap = chunk_overlap_val
                st.session_state.top_k = top_k_val
                st.session_state.min_similarity = min_similarity_val
                st.session_state.hybrid_alpha = hybrid_alpha_val
                st.toast("Settings updated successfully!", icon="⚙️")

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
                            chunk_size=st.session_state.chunk_size,
                            chunk_overlap=st.session_state.chunk_overlap
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
                        top_k=st.session_state.top_k,
                        min_similarity=st.session_state.min_similarity,
                        hybrid_alpha=st.session_state.hybrid_alpha
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
