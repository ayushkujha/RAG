import os
import json
import re
import numpy as np
from pypdf import PdfReader
from google import genai
from google.genai import types

class RAGEngine:
    def __init__(self, provider="Gemini", api_key=None):
        self.provider = provider
        self.api_key = api_key or (os.environ.get("GEMINI_API_KEY") if provider == "Gemini" else os.environ.get("OPENAI_API_KEY"))
        self.client = None
        self.openai_client = None
        
        self.set_api_key(self.api_key, provider)
        
        # In-memory document storage: list of dicts
        self.documents = []
        self.storage_file = "rag_storage.json"
        self.load_index()

    def set_api_key(self, api_key, provider="Gemini"):
        """Dynamically update the API key, provider, and clients."""
        self.api_key = api_key
        self.provider = provider
        if provider == "OpenAI":
            if api_key:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=api_key)
            self.client = None
        else:
            if api_key:
                self.client = genai.Client(api_key=api_key)
            self.openai_client = None

    def extract_text_from_pdf(self, file_path):
        """Extract text from a PDF file with page number tracking."""
        reader = PdfReader(file_path)
        pages_content = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_content.append({"text": text, "page": idx + 1})
        return pages_content

    def extract_text_from_docx(self, file_path):
        """Extract text from a Word document (.docx)."""
        import docx
        doc = docx.Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return [{"text": "\n".join(paragraphs), "page": 1}]

    def extract_text_from_csv(self, file_path):
        """Extract rows from a CSV file."""
        import csv
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if any(row):
                    rows.append(" | ".join([cell.strip() for cell in row]))
        return [{"text": "\n".join(rows), "page": 1}]

    def extract_text_from_xlsx(self, file_path):
        """Extract rows from an Excel workbook (.xlsx)."""
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheets_content = []
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            sheet_rows = []
            for row in sheet.iter_rows(values_only=True):
                if any(row):
                    sheet_rows.append(" | ".join([str(val).strip() if val is not None else "" for val in row]))
            if sheet_rows:
                sheets_content.append(f"### Sheet: {sheet_name}\n" + "\n".join(sheet_rows))
        return [{"text": "\n\n".join(sheets_content), "page": 1}]

    def chunk_text(self, text_blocks, chunk_size=500, chunk_overlap=100, use_parent_child=False):
        """
        Split text blocks into child chunks. If use_parent_child is True,
        it creates larger parent chunks and nests smaller child chunks inside them.
        """
        chunks = []
        
        for block in text_blocks:
            text = block["text"]
            page = block["page"]
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if use_parent_child:
                # Parent size is larger (e.g. 2.5x child size)
                parent_size = int(chunk_size * 2.5)
                parent_overlap = int(chunk_overlap * 2)
                
                p_start = 0
                while p_start < len(text):
                    p_end = p_start + parent_size
                    parent_chunk = text[p_start:p_end]
                    
                    # Create child chunks from this parent context
                    c_start = 0
                    while c_start < len(parent_chunk):
                        c_end = c_start + chunk_size
                        child_text = parent_chunk[c_start:c_end]
                        
                        chunks.append({
                            "text": child_text,
                            "parent_text": parent_chunk,
                            "metadata": {
                                "page": page,
                                "char_start": p_start + c_start,
                                "char_end": p_start + min(c_end, len(parent_chunk)),
                                "parent_char_start": p_start,
                                "parent_char_end": min(p_end, len(text))
                            }
                        })
                        
                        c_start += (chunk_size - chunk_overlap)
                        
                    p_start += (parent_size - parent_overlap)
            else:
                start = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk_text = text[start:end]
                    
                    chunks.append({
                        "text": chunk_text,
                        "parent_text": chunk_text,
                        "metadata": {
                            "page": page,
                            "char_start": start,
                            "char_end": min(end, len(text))
                        }
                    })
                    
                    start += (chunk_size - chunk_overlap)
                    
        return chunks

    def get_embedding(self, text):
        """Generate embedding vector using selected provider."""
        if self.provider == "OpenAI":
            if not self.openai_client:
                raise ValueError("OpenAI API key is not configured. Please check your credentials.")
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        # Gemini Embedding logic
        if not self.client:
            raise ValueError("Gemini API key is not configured. Please check your credentials.")
        
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
                
        # Fallback if list models succeeds
        try:
            available_models = [m.name for m in self.client.models.list()]
            emb_models = [name for name in available_models if "embed" in name.lower()]
            raise Exception(f"Failed to generate embeddings. Available models: {emb_models}. Error: {last_err}")
        except Exception as list_err:
            raise Exception(f"Failed to generate embeddings. Error: {last_err}. List error: {list_err}")

    def add_document(self, file_name, file_path, chunk_size=500, chunk_overlap=100, use_parent_child=False):
        """Parse, chunk, embed in batches, and add a document to the index."""
        ext = file_name.split('.')[-1].lower()
        if ext == "pdf":
            text_blocks = self.extract_text_from_pdf(file_path)
        elif ext == "docx":
            text_blocks = self.extract_text_from_docx(file_path)
        elif ext == "csv":
            text_blocks = self.extract_text_from_csv(file_path)
        elif ext in ["xlsx", "xls"]:
            text_blocks = self.extract_text_from_xlsx(file_path)
        else:
            # Fallback for txt and markdown
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            text_blocks = [{"text": content, "page": 1}]

        chunks = self.chunk_text(text_blocks, chunk_size, chunk_overlap, use_parent_child)
        
        # Batch size for embedding calls
        batch_size = 100
        total_chunks = len(chunks)
        
        for idx in range(0, total_chunks, batch_size):
            batch = chunks[idx:idx + batch_size]
            batch_texts = [chunk["text"] for chunk in batch]
            
            # Generate embeddings for the batch
            if self.provider == "OpenAI":
                if not self.openai_client:
                    raise ValueError("OpenAI API key is not configured.")
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch_texts
                )
                embeddings = [emb.embedding for emb in response.data]
            else:
                if not self.client:
                    raise ValueError("Gemini API key is not configured.")
                
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
                    "parent_text": chunk["parent_text"],
                    "embedding": embeddings[i],
                    "metadata": chunk["metadata"],
                    "provider": self.provider
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
                # Migrate legacy schema
                for doc in self.documents:
                    if "provider" not in doc:
                        doc["provider"] = "Gemini"
                    if "parent_text" not in doc:
                        doc["parent_text"] = doc["text"]
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

    def _generate_text(self, prompt, system_instruction=None, temperature=0.2):
        """Call either Gemini or OpenAI to generate text."""
        if self.provider == "OpenAI":
            if not self.openai_client:
                raise ValueError("OpenAI API key is not configured.")
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        else:
            if not self.client:
                raise ValueError("Gemini API key is not configured.")
            
            config = types.GenerateContentConfig(
                temperature=temperature
            )
            if system_instruction:
                config.system_instruction = system_instruction
                
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            return response.text

    def generate_suggested_questions(self):
        """Sample documents and generate 3 interesting questions using the selected LLM."""
        if not self.documents:
            return []
            
        provider_docs = [d for d in self.documents if d.get("provider", "Gemini") == self.provider]
        if not provider_docs:
            return []
            
        step = max(1, len(provider_docs) // 5)
        sampled_chunks = provider_docs[::step][:5]
        context_preview = "\n\n".join([c["text"] for c in sampled_chunks])
        
        prompt = (
            "Analyze the following document snippets and generate 3 distinct, interesting, "
            "and highly specific questions that a user could ask to learn about this document. "
            "Return ONLY the 3 questions as a plain list, with one question per line, without any numbering, bullet points, or introductory text.\n\n"
            f"Snippets:\n{context_preview}"
        )
        
        try:
            res_text = self._generate_text(prompt, temperature=0.7)
            questions = [q.strip().lstrip("0123456789.-*• ").strip() for q in res_text.split("\n")]
            return [q for q in questions if q][:3]
        except Exception as e:
            print(f"Error generating suggested questions: {e}")
            return ["Summarize the main topics of this document.", "What are the key takeaways from this document?", "Explain the core concepts discussed here."]

    def _query_expansion(self, query):
        """Generate alternative search queries to improve recall."""
        prompt = (
            f"Generate 3 short alternative search queries (synonyms, different phrasing) to retrieve relevant document chunks for the query: '{query}'. "
            "Return them as a simple list separated by newlines, with one query per line, without numbering or extra words."
        )
        try:
            res_text = self._generate_text(prompt, temperature=0.6)
            queries = [q.strip().lstrip("0123456789.-*• ").strip() for q in res_text.split("\n") if q.strip()]
            return [query] + queries[:3]
        except Exception as e:
            print(f"Error in query expansion: {e}")
            return [query]

    def _generate_hyde_answer(self, query):
        """Generate a hypothetical document answering the query to retrieve semantically matching content."""
        prompt = (
            f"Write a short, direct paragraph answering the question: '{query}'. "
            "Write what a helpful reference document would say. Do not introduce it, do not worry about actual facts, just write the paragraph."
        )
        try:
            return self._generate_text(prompt, temperature=0.7)
        except Exception as e:
            print(f"Error in HyDE generation: {e}")
            return query

    def _rerank_chunks(self, query, chunks, top_k=4):
        """Rerank retrieved chunks using the LLM to sort by relevance."""
        if not chunks:
            return []
            
        snippets_list = []
        for idx, chunk in enumerate(chunks):
            text = chunk.get("parent_text", chunk["text"])
            snippets_list.append(f"[Index {idx}] source: {chunk['metadata']['source']}\nContent: {text[:600]}")
            
        snippets_text = "\n\n".join(snippets_list)
        
        prompt = (
            f"User Query: {query}\n\n"
            "Evaluate the following retrieved document snippets and rank them based on how useful they are to answer the query. "
            "Return a JSON array of integers representing the 0-based indices of the snippets in order of relevance (most relevant first), e.g. [2, 0, 1]. "
            "Only return the JSON array, with no other text, commentary, or markdown blocks.\n\n"
            f"Snippets:\n{snippets_text}"
        )
        
        try:
            res_text = self._generate_text(prompt, temperature=0.1)
            match = re.search(r'\[\s*\d+\s*(?:,\s*\d+\s*)*\]', res_text)
            if match:
                order = json.loads(match.group(0))
                ranked_chunks = []
                seen_indices = set()
                for idx in order:
                    if 0 <= idx < len(chunks) and idx not in seen_indices:
                        ranked_chunks.append(chunks[idx])
                        seen_indices.add(idx)
                for idx, chunk in enumerate(chunks):
                    if idx not in seen_indices:
                        ranked_chunks.append(chunk)
                return ranked_chunks[:top_k]
        except Exception as e:
            print(f"Error in reranking: {e}")
            
        return chunks[:top_k]

    def retrieve(self, query, top_k=4, min_similarity=0.25, hybrid_alpha=0.7, enhancement="None", rerank=False):
        """Retrieve top chunks using hybrid search, query expansion/HyDE, and reranking."""
        provider_docs = [d for d in self.documents if d.get("provider", "Gemini") == self.provider]
        if not provider_docs:
            return []
            
        search_queries = [query]
        if enhancement == "Query Expansion":
            search_queries = self._query_expansion(query)
        elif enhancement == "HyDE":
            hyde_answer = self._generate_hyde_answer(query)
            search_queries = [hyde_answer]

        all_results = {}
        for q in search_queries:
            q_emb = np.array(self.get_embedding(q))
            q_terms = set(re.findall(r'\b\w{3,}\b', q.lower()))
            
            for doc in provider_docs:
                doc_id = doc["id"]
                doc_embedding = np.array(doc["embedding"])
                
                # Cosine Similarity
                dot_prod = np.dot(q_emb, doc_embedding)
                norm_q = np.linalg.norm(q_emb)
                norm_d = np.linalg.norm(doc_embedding)
                similarity = float(dot_prod / (norm_q * norm_d)) if norm_q > 0 and norm_d > 0 else 0.0
                
                # Keyword Score
                keyword_score = 0.0
                if q_terms:
                    doc_terms = set(re.findall(r'\b\w{3,}\b', doc["text"].lower()))
                    matches = q_terms.intersection(doc_terms)
                    keyword_score = len(matches) / len(q_terms)
                    
                hybrid_score = (hybrid_alpha * similarity) + ((1.0 - hybrid_alpha) * keyword_score)
                
                if similarity >= min_similarity or hybrid_score >= min_similarity:
                    res_item = {
                        "text": doc["text"],
                        "parent_text": doc.get("parent_text", doc["text"]),
                        "metadata": doc["metadata"],
                        "similarity": similarity,
                        "keyword_score": keyword_score,
                        "hybrid_score": hybrid_score
                    }
                    if doc_id not in all_results or hybrid_score > all_results[doc_id]["hybrid_score"]:
                        all_results[doc_id] = res_item
                        
        results = list(all_results.values())
        results = sorted(results, key=lambda x: x["hybrid_score"], reverse=True)
        
        candidates_k = top_k * 2 if rerank else top_k
        candidates = results[:candidates_k]
        
        if rerank:
            return self._rerank_chunks(query, candidates, top_k)
        
        return candidates[:top_k]

    def query_with_context(self, query, chat_history=None, top_k=4, min_similarity=0.25, hybrid_alpha=0.7, enhancement="None", rerank=False):
        """Query LLM combining retrieved context and conversation history."""
        retrieved_chunks = self.retrieve(
            query=query, 
            top_k=top_k, 
            min_similarity=min_similarity, 
            hybrid_alpha=hybrid_alpha, 
            enhancement=enhancement, 
            rerank=rerank
        )
        
        context_str = ""
        if retrieved_chunks:
            context_str = "\n\n".join([
                f"[Source: {c['metadata']['source']} (Page {c['metadata']['page']}), Similarity: {c['similarity']:.2f}]\n{c.get('parent_text', c['text'])}"
                for c in retrieved_chunks
            ])
        else:
            context_str = "No relevant context found in database."
            
        system_instruction = (
            "You are a helpful assistant. You answer the user's questions based strictly on the provided context. "
            "If the context does not contain the answer, politely say so. Do not make up information. "
            "Always cite the source document name and page number when referencing information from the context."
        )
        
        current_prompt = (
            f"Context from uploaded documents:\n{context_str}\n\n"
            f"User Question: {query}"
        )
        
        if self.provider == "OpenAI":
            if not self.openai_client:
                raise ValueError("OpenAI API key is not configured. Please check your credentials.")
            messages = [{"role": "system", "content": system_instruction}]
            if chat_history:
                for msg in chat_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": current_prompt})
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2
            )
            response_text = response.choices[0].message.content
        else:
            if not self.client:
                raise ValueError("Gemini API key is not configured. Please check your credentials.")
            
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
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2
                )
            )
            response_text = response.text
            
        return response_text, retrieved_chunks
