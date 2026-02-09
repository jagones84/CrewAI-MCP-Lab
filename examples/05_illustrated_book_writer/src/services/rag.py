import os
try:
    import chromadb
except ImportError:
    chromadb = None
    print("WARNING: chromadb not installed. RAG memory will not work.")

from datetime import datetime

class KnowledgeBase:
    def __init__(self, book_title="default_book", db_path="./rag_db", collection_suffix="_narrative"):
        if not chromadb: return
        
        # Sanitize title for collection name
        safe_title = "".join([c if c.isalnum() else "_" for c in book_title]).lower()
        safe_title = safe_title[:50]
        
        self.client = chromadb.PersistentClient(path=db_path)
        col_name = f"{safe_title}{collection_suffix}"
        self.narrative_col = self.client.get_or_create_collection(name=col_name)
    
    def add_narrative(self, text, title, summary):
        if not chromadb: return
        ts = datetime.now().timestamp()
        # Add text and summary to index
        self.narrative_col.add(documents=[text], metadatas=[{"chapter": title, "type": "full_text"}], ids=[f"txt_{ts}"])
        self.narrative_col.add(documents=[summary], metadatas=[{"chapter": title, "type": "summary"}], ids=[f"sum_{ts}"])

    def query_context(self, query, n_results=3):
        if not chromadb: return "No Memory."
        # Query for relevant past context
        res = self.narrative_col.query(query_texts=[query], n_results=n_results)
        return "\n".join(res['documents'][0]) if res['documents'] else "No Context."
