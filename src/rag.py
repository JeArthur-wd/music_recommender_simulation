"""
Retrieval-Augmented Generation (RAG) support: a small knowledge base of music
guidance plus a BM25 retriever, written in pure Python (no extra dependencies).

The knowledge base (data/knowledge_base.json) holds short documents about
genres, activities ("studying", "workout"), contexts ("rainy day") and moods.
Each document has prose `text` and structured `hints` (genre, mood, energy...).

The agent retrieves the documents most relevant to a request and uses them to
ground the profile it builds: the rule-based planner reads their hints, and the
optional LLM planner receives their text as context. Retrieved document titles
are returned as sources so every answer can be traced to its evidence.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

try:
    from .logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger("rag")

DEFAULT_KB_PATH = "data/knowledge_base.json"
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "to", "of", "in", "on", "at", "with",
    "me", "my", "i", "im", "i'm", "some", "something", "song", "songs", "music", "track",
    "tracks", "play", "want", "need", "like", "please", "give", "that", "this", "is", "it",
    "be", "are", "while", "when", "from", "by", "up", "can", "you", "your", "get", "listen",
    "listening", "recommend", "playlist", "really", "very", "just", "kind", "sort", "feel",
}
BM25_K1 = 1.5
BM25_B = 0.75
KEYWORD_BOOST = 3  # keywords count this many times, so curated terms beat incidental prose


def stem(token: str) -> str:
    """A tiny suffix stripper so 'studying'/'study' and 'beats'/'beat' match."""
    for suffix in ("ing", "ies", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            return token + "y" if suffix == "ies" else token
    return token


def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-letters (keeping '&' for 'r&b'), drop stopwords, stem."""
    words = re.findall(r"[a-z0-9&]+", text.lower().replace("-", " "))
    return [stem(w) for w in words if w not in STOPWORDS]


@dataclass
class Document:
    """One knowledge-base entry."""
    id: str
    type: str
    title: str
    text: str
    keywords: List[str]
    hints: Dict


@dataclass
class Retrieved:
    """A document returned by the retriever with its relevance score."""
    doc: Document
    score: float


class KnowledgeBase:
    """Loads documents and ranks them against a query with BM25."""

    def __init__(self, documents: List[Document]):
        if not documents:
            raise ValueError("Knowledge base is empty.")
        self.documents = documents
        self._tokens = [self._doc_tokens(doc) for doc in documents]
        self._avg_len = sum(len(t) for t in self._tokens) / len(self._tokens)
        doc_freq = Counter(term for tokens in self._tokens for term in set(tokens))
        n = len(documents)
        self._idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5)) for term, df in doc_freq.items()
        }

    @classmethod
    def load(cls, path: str = DEFAULT_KB_PATH) -> "KnowledgeBase":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        docs = [
            Document(d["id"], d["type"], d["title"], d["text"], d.get("keywords", []), d.get("hints", {}))
            for d in raw
        ]
        logger.info("Loaded %d knowledge-base documents from %s", len(docs), path)
        return cls(docs)

    @staticmethod
    def _doc_tokens(doc: Document) -> List[str]:
        keyword_tokens = tokenize(" ".join(doc.keywords)) * KEYWORD_BOOST
        return tokenize(doc.title) + keyword_tokens + tokenize(doc.text)

    def retrieve(self, query: str, k: int = 4, min_score: float = 1.0) -> List[Retrieved]:
        """Return up to k documents whose BM25 score is at least min_score, best first."""
        query_terms = tokenize(query)
        # Multi-word keywords ("road trip", "date night") also match as phrases
        lowered = " " + " ".join(re.findall(r"[a-z0-9&]+", query.lower().replace("-", " "))) + " "
        results = []
        for doc, tokens in zip(self.documents, self._tokens):
            counts = Counter(tokens)
            norm = BM25_K1 * (1 - BM25_B + BM25_B * len(tokens) / self._avg_len)
            score = 0.0
            for term in set(query_terms):
                tf = counts.get(term, 0)
                if tf:
                    score += self._idf.get(term, 0) * tf * (BM25_K1 + 1) / (tf + norm)
            for phrase in doc.keywords:
                normalized = " ".join(re.findall(r"[a-z0-9&]+", phrase.lower().replace("-", " ")))
                if " " in normalized and f" {normalized} " in lowered:
                    score += 2.0
            if score >= min_score:
                results.append(Retrieved(doc, round(score, 3)))
        results.sort(key=lambda r: (-r.score, r.doc.id))
        top = results[:k]
        logger.debug("Retrieved for %r: %s", query, [(r.doc.id, r.score) for r in top])
        return top
