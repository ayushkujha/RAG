# RAG Navigator

An intelligent, full-fledged Retrieval-Augmented Generation (RAG) assistant that allows users to upload documents (PDF, TXT, MD) and converse with their content using Google's Gemini models with source citations.

## Features

- **Hybrid Keyword-Vector Search**: Combines semantic embeddings (via `gemini-embedding-001`) with text-overlap matching (TF-IDF equivalent) for highly precise search results.
- **Interactive Web Interface**: Sleek Streamlit dashboard for document upload, index statistics, parameter fine-tuning, and chat.
- **AI Suggested Questions**: Automatically parses documents to suggest relevant prompt buttons.
- **Dynamic File Manager**: View indexed document chunk metrics and selectively delete files.
- **Chat Exporter**: Download conversation histories as clean Markdown.

## Quick Start (Local Run)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ayushkujha/RAG.git
   cd RAG
   ```

2. **Initialize virtual environment & install packages:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\pip install -r requirements.txt
   # macOS/Linux:
   .venv/bin/pip install -r requirements.txt
   ```

3. **Launch the application:**
   ```bash
   # Windows:
   .venv\Scripts\streamlit run app.py
   # macOS/Linux:
   .venv/bin/streamlit run app.py
   ```

4. Open your browser and navigate to `http://localhost:8501`. Add your **Gemini API Key** in the sidebar settings, upload a file, and start querying.
