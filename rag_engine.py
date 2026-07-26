import os
import re
import fitz  # PyMuPDF
import chromadb
from pypdf import PdfReader
from google import genai
from google.genai import types

class RAGEngine:
    def __init__(self, api_key=None, db_path="./chroma_db"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            
        # Initialize persistent ChromaDB Vector Store
        self.db_path = db_path
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def set_api_key(self, api_key):
        """Dynamically update API key and GenAI client."""
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)

    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF page by page using PyMuPDF (fitz), fallback to pypdf."""
        pages_content = []
        try:
            doc = fitz.open(file_path)
            for idx, page in enumerate(doc):
                text = page.get_text("text")
                if text and text.strip():
                    pages_content.append({"text": text, "page": idx + 1})
            doc.close()
        except Exception as e:
            # Fallback to PyPDF if PyMuPDF encounters an issue
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages_content.append({"text": text, "page": idx + 1})
                    
        return pages_content

    def chunk_text(self, text_blocks, chunk_size=800, chunk_overlap=150):
        """Split text blocks into overlapping chunks with page metadata."""
        chunks = []
        for block in text_blocks:
            text = block["text"]
            page = block["page"]
            text = re.sub(r'\s+', ' ', text).strip()
            
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "page": page,
                        "char_start": start,
                        "char_end": min(end, len(text))
                    }
                })
                start += (chunk_size - chunk_overlap)
                
        return chunks

    def get_embedding(self, text):
        """Generate vector embedding using Google GenAI SDK."""
        if not self.client:
            # Attempt to re-initialize client from environment variable
            env_key = os.environ.get("GEMINI_API_KEY")
            if env_key:
                self.client = genai.Client(api_key=env_key)
            else:
                raise ValueError("Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable.")
                
        embedding_models = ["gemini-embedding-001", "gemini-embedding-2", "gemini-embedding-2-preview"]
        last_err = None
        
        # If input is a list of texts vs single string
        contents = text if isinstance(text, list) else [text]
        
        for model_name in embedding_models:
            try:
                response = self.client.models.embed_content(
                    model=model_name,
                    contents=contents
                )
                if response.embeddings:
                    return [emb.values for emb in response.embeddings] if isinstance(text, list) else response.embeddings[0].values
                elif hasattr(response, 'embedding') and response.embedding:
                    return [emb.values for emb in response.embedding] if isinstance(text, list) else response.embedding.values
            except Exception as e:
                last_err = e
                continue
                
        raise Exception(f"Failed to generate embeddings: {last_err}")

    def add_document(self, file_name, file_path, chunk_size=800, chunk_overlap=150):
        """Extract text, chunk, embed, and store document in ChromaDB."""
        text_blocks = self.extract_text_from_pdf(file_path)
        if not text_blocks:
            # Fallback for plain text files if uploaded
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            text_blocks = [{"text": content, "page": 1}]

        chunks = self.chunk_text(text_blocks, chunk_size, chunk_overlap)
        if not chunks:
            return 0

        batch_size = 50
        total_chunks = len(chunks)
        
        for idx in range(0, total_chunks, batch_size):
            batch = chunks[idx:idx + batch_size]
            batch_texts = [c["text"] for c in batch]
            
            embeddings = self.get_embedding(batch_texts)
            
            ids = []
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(batch):
                global_idx = idx + i
                chunk_id = f"{file_name}_chunk_{global_idx}"
                ids.append(chunk_id)
                documents.append(chunk["text"])
                metadatas.append({
                    "source": file_name,
                    "page": int(chunk["metadata"]["page"]),
                    "chunk_index": int(global_idx)
                })
                
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
        return total_chunks

    def get_indexed_documents(self):
        """Retrieve list of indexed unique document filenames and total chunk count from ChromaDB."""
        data = self.collection.get(include=["metadatas"])
        metadatas = data.get("metadatas", [])
        
        doc_counts = {}
        for meta in metadatas:
            src = meta.get("source", "Unknown")
            doc_counts[src] = doc_counts.get(src, 0) + 1
            
        return doc_counts

    def count_chunks(self):
        """Return total number of chunks stored in ChromaDB."""
        return self.collection.count()

    def delete_document(self, file_name):
        """Delete all chunks belonging to a specific document from ChromaDB."""
        self.collection.delete(where={"source": file_name})
        return True

    def clear_index(self):
        """Reset the ChromaDB collection completely."""
        self.chroma_client.delete_collection("pdf_documents")
        self.collection = self.chroma_client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )
        return True

    def retrieve(self, query, top_k=4):
        """Query ChromaDB using semantic embedding search."""
        if self.collection.count() == 0:
            return []

        query_embedding = self.get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        if results and results["documents"] and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0]*len(docs)
            
            for doc_text, meta, dist in zip(docs, metas, distances):
                # Convert cosine distance to similarity score
                similarity = 1.0 - dist if dist <= 1.0 else (1.0 / (1.0 + dist))
                chunks.append({
                    "text": doc_text,
                    "metadata": meta,
                    "similarity": similarity
                })

        return chunks

    def query_with_context(self, query, chat_history=None, top_k=4):
        """Retrieve context from ChromaDB and generate an answer using Gemini."""
        retrieved_chunks = self.retrieve(query, top_k=top_k)
        
        if retrieved_chunks:
            context_blocks = []
            for chunk in retrieved_chunks:
                source = chunk["metadata"].get("source", "Document")
                page = chunk["metadata"].get("page", 1)
                context_blocks.append(f"[Source: {source}, Page: {page}]\n{chunk['text']}")
            context_str = "\n\n".join(context_blocks)
        else:
            context_str = "No relevant document chunks found in database."

        system_instruction = (
            "You are an AI Study & Research Assistant. You help users understand and chat about their uploaded PDF documents.\n"
            "Answer questions accurately based ONLY on the provided document context snippets.\n"
            "If the context does not contain enough information to answer the question, state politely that the uploaded documents do not contain that information.\n"
            "Always cite the relevant document name and page number when answering."
        )

        current_prompt = (
            f"Context from uploaded PDF documents:\n{context_str}\n\n"
            f"User Question: {query}"
        )

        messages = []
        if chat_history:
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                messages.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
                
        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=current_prompt)]
        ))

        if not self.client:
            env_key = os.environ.get("GEMINI_API_KEY")
            if env_key:
                self.client = genai.Client(api_key=env_key)
            else:
                raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY environment variable.")

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )

        return response.text, retrieved_chunks

    def generate_suggested_questions(self):
        """Generate 3 tailored questions based on indexed document snippets."""
        if self.collection.count() == 0:
            return []
            
        data = self.collection.get(limit=5, include=["documents"])
        docs = data.get("documents", [])
        if not docs:
            return []
            
        context_preview = "\n\n".join(docs[:3])
        prompt = (
            "Based on these PDF document snippets, generate 3 clear, interesting, and specific questions a user could ask to study this content.\n"
            "Return ONLY the 3 questions as a plain list, one question per line, with no bullet points or extra text.\n\n"
            f"Snippets:\n{context_preview}"
        )
        
        try:
            if not self.client:
                env_key = os.environ.get("GEMINI_API_KEY")
                if env_key:
                    self.client = genai.Client(api_key=env_key)
                else:
                    return []
                    
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            questions = [q.strip().lstrip("0123456789.-*• ").strip() for q in response.text.split("\n") if q.strip()]
            return questions[:3]
        except Exception:
            return ["Summarize the main points of this PDF.", "What are the key concepts explained here?", "What conclusions does this document reach?"]
