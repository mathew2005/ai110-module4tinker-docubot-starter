"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob


class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        self.docs_folder = docs_folder
        self.llm_client = llm_client
        self.documents = self.load_documents()   # list of (chunk_id, text)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def chunk_text(self, text):
        """Split a document into paragraphs on blank lines, drop empties."""
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def load_documents(self):
        """
        Read every .md and .txt file in docs_folder, split each into
        paragraphs, and return a flat list of (chunk_id, text) tuples.
        chunk_id format: "filename::para_0", "filename::para_1", etc.
        """
        chunks = []
        for path in glob.glob(os.path.join(self.docs_folder, "*.*")):
            if not (path.endswith(".md") or path.endswith(".txt")):
                continue
            with open(path, "r", encoding="utf8") as f:
                text = f.read()
            filename = os.path.basename(path)
            for i, para in enumerate(self.chunk_text(text)):
                chunks.append((f"{filename}::para_{i}", para))
        return chunks

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        Inverted index: maps each lowercase word to the chunk IDs that contain it.
        { "token": ["AUTH.md::para_2", ...], "database": ["DATABASE.md::para_1"] }
        """
        index = {}
        for chunk_id, text in documents:
            for word in set(text.lower().split()):
                index.setdefault(word, [])
                if chunk_id not in index[word]:
                    index[word].append(chunk_id)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def _content_words(self, query):
        """Return lowercase query words that are 3+ characters (filters stop words)."""
        return [w for w in query.lower().split() if len(w) >= 3]

    def score_document(self, query, text):
        """
        Count how many times each content word from the query appears in text.
        More occurrences = higher score = more relevant.
        """
        words = self._content_words(query)
        if not words:
            return 0
        text_lower = text.lower()
        return sum(text_lower.count(w) for w in words)

    def retrieve(self, query, top_k=3, min_score=3):
        """
        Find the top_k most relevant chunks for a query.
        Chunks scoring below min_score are dropped — that's the guardrail.
        Returns a list of (chunk_id, text) sorted best-first.
        """
        words = self._content_words(query)
        if not words:
            return []

        # Use the index to narrow down to chunks that share at least one word
        candidates = set()
        for w in words:
            if w in self.index:
                candidates.update(self.index[w])

        if not candidates:
            return []

        # Score each candidate and keep only those above the threshold
        scored = [
            (self.score_document(query, text), chunk_id, text)
            for chunk_id, text in self.documents
            if chunk_id in candidates
        ]
        scored = [(s, cid, t) for s, cid, t in scored if s >= min_score]
        scored.sort(reverse=True, key=lambda x: x[0])

        return [(cid, t) for _, cid, t in scored[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3, min_score=3):
        """Mode 2: return raw matching chunks, no LLM."""
        snippets = self.retrieve(query, top_k=top_k, min_score=min_score)
        if not snippets:
            return "I do not know based on these docs."
        return "\n---\n".join(f"[{cid}]\n{text}\n" for cid, text in snippets)

    def answer_rag(self, query, top_k=3, min_score=3):
        """Mode 3: retrieve first, then let the LLM synthesize from those chunks only."""
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )
        snippets = self.retrieve(query, top_k=top_k, min_score=min_score)
        if not snippets:
            return "I do not know based on these docs."
        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Helper for naive LLM mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """Concatenate all chunks into one string for Phase 0 naive generation."""
        return "\n\n".join(text for _, text in self.documents)