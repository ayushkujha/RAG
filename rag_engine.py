import os
import json
import re
import numpy as np
from pypdf import PdfReader
from google import genai
from google.genai import types

class RAGEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        
        # In-memory document storage: list of dicts with keys: id, text, metadata, embedding
        self.documents = []
        # Local storage filepath
        self.storage_file = "rag_storage.json"
        self.load_index()

    def set_api_key(self, api_key):
        """Dynamically update the API key and client."""
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    def extract_text_from_pdf(self, file_path):
        """Extract text from a PDF file with page number tracking."""
        reader = PdfReader(file_path)
        pages_content = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_content.append({"text": text, "page": idx + 1})
        return pages_content

    def chunk_text(self, text_blocks, chunk_size=500, chunk_overlap=100):
        """
        Split text blocks (containing page info) into chunks of a given character size
        with overlapping windows.
        """
        chunks = []
        
        for block in text_blocks:
            text = block["text"]
            page = block["page"]
            
            # Clean up whitespace
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
                
                # Advance starting pointer
                start += (chunk_size - chunk_overlap)
                
        return chunks

    def get_embedding(self, text):
        """Generate embedding vector using the Google GenAI SDK, with fallback for model naming changes."""
        if not self.client:
            raise ValueError("Gemini API key is not configured. Please check your credentials.")
        
        # Try verified embedding model identifiers
        embedding_models = ["gemini-embedding-001", "gemini-embedding-2", "gemini-embedding-2-preview"]
        
        last_err = None
        for model_name in embedding_models:
            try:
                response = self.client.models.embed_content(
                    model=model_name,
                    contents=text
                )
                if response.embeddings:
                    return response.embeddings[0].values
                elif hasattr(response, 'embedding') and response.embedding:
                    return response.embedding.values
            except Exception as e:
                last_err = e
                continue
                
        # If all fail, try to list models and raise a descriptive error
        try:
            available_models = [m.name for m in self.client.models.list()]
            emb_models = [name for name in available_models if "embed" in name.lower()]
            raise Exception(f"Failed to generate embeddings. Available embedding models: {emb_models}. Error: {last_err}")
        except Exception as list_err:
            raise Exception(f"Failed to generate embeddings. Error: {last_err}. List models error: {list_err}")

    def add_document(self, file_name, file_path, chunk_size=500, chunk_overlap=100):
        """Parse, chunk, embed in batches, and add a document to the index."""
        if file_path.lower().endswith(".pdf"):
            text_blocks = self.extract_text_from_pdf(file_path)
        else:
            # Fallback for txt and markdown
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            text_blocks = [{"text": content, "page": 1}]

        chunks = self.chunk_text(text_blocks, chunk_size, chunk_overlap)
        
        # Batch size for embedding calls
        batch_size = 100
        total_chunks = len(chunks)
        
        for idx in range(0, total_chunks, batch_size):
            batch = chunks[idx:idx + batch_size]
            batch_texts = [chunk["text"] for chunk in batch]
            
            # Generate embeddings for the batch
            if not self.client:
                raise ValueError("Gemini API key is not configured. Please check your credentials.")
            
            # Try verified embedding model identifiers
            embedding_models = ["gemini-embedding-001", "gemini-embedding-2", "gemini-embedding-2-preview"]
            embeddings = None
            last_err = None
            
            for model_name in embedding_models:
                try:
                    response = self.client.models.embed_content(
                        model=model_name,
                        contents=batch_texts
                    )
                    if response.embeddings:
                        embeddings = [emb.values for emb in response.embeddings]
                        break
                    elif hasattr(response, 'embedding') and response.embedding:
                        embeddings = [emb.values for emb in response.embedding]
                        break
                except Exception as e:
                    last_err = e
                    continue
            
            if not embeddings:
                raise Exception(f"Failed to generate batch embeddings. Error: {last_err}")
                
            # Store chunks with their embeddings
            for i, chunk in enumerate(batch):
                global_idx = idx + i
                chunk["metadata"]["source"] = file_name
                chunk["metadata"]["chunk_index"] = global_idx
                
                self.documents.append({
                    "id": f"{file_name}_chunk_{global_idx}",
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "embedding": embeddings[i]
                })
            
        self.save_index()
        return total_chunks

    def save_index(self):
        """Serialize index to local storage file."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving index: {e}")

    def load_index(self):
        """Deserialize index from local storage file if exists."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception as e:
                print(f"Error loading index: {e}")
                self.documents = []

    def clear_index(self):
        """Reset index and delete local storage."""
        self.documents = []
        if os.path.exists(self.storage_file):
            try:
                os.remove(self.storage_file)
            except Exception as e:
                print(f"Error removing storage file: {e}")

    def delete_document(self, file_name):
        """Remove all chunks associated with a specific file name and update index."""
        initial_count = len(self.documents)
        self.documents = [doc for doc in self.documents if doc["metadata"]["source"] != file_name]
        removed_count = initial_count - len(self.documents)
        self.save_index()
        return removed_count

    def generate_suggested_questions(self):
        """Sample documents and generate 3 interesting questions using Gemini."""
        if not self.documents or not self.client:
            return []
            
        # Sample up to 5 chunks spread across the documents
        step = max(1, len(self.documents) // 5)
        sampled_chunks = self.documents[::step][:5]
        context_preview = "\n\n".join([c["text"] for c in sampled_chunks])
        
        prompt = (
            "Analyze the following document snippets and generate 3 distinct, interesting, "
            "and highly specific questions that a user could ask to learn about this document. "
            "Return ONLY the 3 questions as a plain list, with one question per line, without any numbering, bullet points, or introductory text.\n\n"
            f"Snippets:\n{context_preview}"
        )
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            # Split lines and clean up
            questions = [q.strip().lstrip("0123456789.-*• ").strip() for q in response.text.split("\n")]
            return [q for q in questions if q][:3]
        except Exception as e:
            print(f"Error generating suggested questions: {e}")
            return ["Summarize the main topics of this document.", "What are the key takeaways from this document?", "Explain the core concepts discussed here."]

    def retrieve(self, query, top_k=4, min_similarity=0.25, hybrid_alpha=0.7):
        """
        Retrieve top_k documents using Hybrid Search (Cosine Similarity + Keyword matching).
        """
        if not self.documents:
            return []
            
        # Vector search
        query_embedding = np.array(self.get_embedding(query))
        
        # Keyword search preprocessing
        # Tokenize query, filter short stop words
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        
        results = []
        for doc in self.documents:
            doc_embedding = np.array(doc["embedding"])
            
            # 1. Calculate cosine similarity
            dot_prod = np.dot(query_embedding, doc_embedding)
            norm_q = np.linalg.norm(query_embedding)
            norm_d = np.linalg.norm(doc_embedding)
            similarity = float(dot_prod / (norm_q * norm_d)) if norm_q > 0 and norm_d > 0 else 0.0
            
            # 2. Calculate keyword matching score
            keyword_score = 0.0
            if query_terms:
                doc_terms = set(re.findall(r'\b\w{3,}\b', doc["text"].lower()))
                matches = query_terms.intersection(doc_terms)
                keyword_score = len(matches) / len(query_terms)
                
            # Blended hybrid score
            hybrid_score = (hybrid_alpha * similarity) + ((1.0 - hybrid_alpha) * keyword_score)
            
            if similarity >= min_similarity or hybrid_score >= min_similarity:
                results.append({
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "similarity": similarity,
                    "keyword_score": keyword_score,
                    "hybrid_score": hybrid_score
                })
                
        # Sort by blended score descending
        results = sorted(results, key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

    def query_with_context(self, query, chat_history=None, top_k=4, min_similarity=0.25, hybrid_alpha=0.7):
        """Query LLM combining retrieved context and optionally conversation history."""
        if not self.client:
            raise ValueError("Gemini API key is not configured. Please check your credentials.")
            
        retrieved_chunks = self.retrieve(query, top_k, min_similarity, hybrid_alpha)
        
        # Build prompt context
        context_str = ""
        if retrieved_chunks:
            context_str = "\n\n".join([
                f"[Source: {c['metadata']['source']} (Page {c['metadata']['page']}), Similarity: {c['similarity']:.2f}]\n{c['text']}"
                for c in retrieved_chunks
            ])
        else:
            context_str = "No relevant context found in database."

        # Setup chat/messages
        messages = []
        
        # Add system instruction
        system_instruction = (
            "You are a helpful assistant. You answer the user's questions based strictly on the provided context. "
            "If the context does not contain the answer, politely say so. Do not make up information. "
            "Always cite the source document name and page number when referencing information from the context."
        )
        
        # If chat history is provided, convert/append it
        if chat_history:
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                messages.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
        
        # Compile current prompt
        current_prompt = (
            f"Context from uploaded documents:\n{context_str}\n\n"
            f"User Question: {query}"
        )
        
        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=current_prompt)]
        ))
        
        # Generate response using gemini-2.5-flash
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )
        
        return response.text, retrieved_chunks
