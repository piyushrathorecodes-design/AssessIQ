import os
import sys
import pickle
import numpy as np
import faiss
import re
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

from app.config.settings import settings
from app.models.domain import Assessment, ConversationState

def tokenize_text(text: str) -> List[str]:
    """Helper to clean and tokenize text for BM25 indexing/querying."""
    text = text.lower()
    # Replace non-alphanumeric with spaces, then split
    tokens = re.sub(r"[^a-z0-9]", " ", text).split()
    return [t for t in tokens if len(t) > 1]

class HybridRetriever:
    """
    Modular Hybrid Retriever combining dense vector search (FAISS) 
    and sparse keyword search (BM25) with metadata filtering.
    """
    def __init__(self, alpha: float = 0.6):
        self.alpha = alpha
        self.model = None
        self.faiss_index = None
        self.assessments: List[Assessment] = []
        self.bm25 = None
        self.load_resources()

    def load_resources(self):
        """Loads index files and models from disk."""
        # 1. Load Embedding Model
        print(f"Retriever: Loading SentenceTransformer {settings.embedding_model} ...")
        self.model = SentenceTransformer(settings.embedding_model)

        # 2. Load FAISS dense index
        if not os.path.exists(settings.faiss_index_path):
            raise FileNotFoundError(f"FAISS index file not found at: {settings.faiss_index_path}")
        print("Retriever: Loading FAISS Index...")
        self.faiss_index = faiss.read_index(settings.faiss_index_path)

        # 3. Load Metadata
        if not os.path.exists(settings.metadata_path):
            raise FileNotFoundError(f"Metadata file not found at: {settings.metadata_path}")
        print("Retriever: Loading Metadata...")
        with open(settings.metadata_path, "rb") as f:
            self.assessments = pickle.load(f)

        # 4. Initialize BM25 Sparse Index
        print("Retriever: Initializing BM25 lexical index...")
        # Import indexing helper inside to avoid circular reference
        from scripts.build_index import build_search_text
        
        tokenized_corpus = []
        for a in self.assessments:
            # We build the same search text block we used for embeddings
            # Convert Assessment object back to dict for build_search_text
            text_repr = build_search_text(a.model_dump())
            tokenized_corpus.append(tokenize_text(text_repr))
            
        self.bm25 = BM25Okapi(tokenized_corpus)
        print("Retriever: Resources initialized successfully.")

    def retrieve(self, query: str, state: Optional[ConversationState] = None, top_k: int = 5) -> List[Assessment]:
        """
        Retrieves relevant assessments using weighted hybrid search and criteria filters.
        """
        # Ensure search top_k is within limits
        k = max(1, min(settings.top_k, top_k))

        # 1. Dense vector search
        query_vector = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)
        # faiss_index.search returns (distances, indices)
        dense_distances, dense_indices = self.faiss_index.search(query_vector, len(self.assessments))
        
        # Build dense scores mapping
        dense_scores = np.zeros(len(self.assessments))
        for dist, idx in zip(dense_distances[0], dense_indices[0]):
            if idx != -1:
                # FlatIP distance represents cosine similarity (already -1 to 1)
                dense_scores[idx] = dist

        # 2. Sparse lexical search (BM25)
        query_tokens = tokenize_text(query)
        bm25_scores = np.array(self.bm25.get_scores(query_tokens))

        # 3. Normalize scores (Min-Max Scaling to align scales between 0.0 and 1.0)
        def normalize(scores):
            min_val = np.min(scores)
            max_val = np.max(scores)
            if max_val - min_val > 1e-6:
                return (scores - min_val) / (max_val - min_val)
            return np.zeros_like(scores)

        norm_dense = normalize(dense_scores)
        norm_sparse = normalize(bm25_scores)

        # 4. Linear combination
        combined_scores = self.alpha * norm_dense + (1.0 - self.alpha) * norm_sparse

        # 5. Apply soft boosting for metadata criteria (Job Role, Skills, Test Types)
        # Soft boosting increases the score rather than hard filtering to avoid empty lists
        boosted_scores = combined_scores.copy()
        
        if state:
            state_test_types = [t.strip().upper() for t in state.test_types if t.strip()]
            state_skills = [s.lower() for s in state.required_skills if s.strip()]
            
            for idx, a in enumerate(self.assessments):
                boost = 0.0
                
                # Check test type overlap (A, B, P, K, S, etc.)
                if state_test_types:
                    a_types = [t.upper() for t in a.test_type]
                    if any(t in a_types for t in state_test_types):
                        boost += 0.3
                        
                # Check skills overlap
                if state_skills:
                    a_skills = [s.lower() for s in a.skills]
                    if any(s in a_skills for s in state_skills):
                        boost += 0.2
                        
                # Check remote support request
                if state.remote_testing is True and a.remote_testing_support:
                    boost += 0.1
                    
                # Check adaptive request
                if state.adaptive is True and a.adaptive:
                    boost += 0.1
                    
                # Check job role similarity
                if state.job_role and a.job_roles:
                    state_role_lower = state.job_role.lower()
                    if any(r.lower() in state_role_lower or state_role_lower in r.lower() for r in a.job_roles):
                        boost += 0.4
                        
                boosted_scores[idx] += boost

        # 6. Sort and return top k matching assessments
        ranked_indices = np.argsort(boosted_scores)[::-1]
        
        retrieved_assessments = []
        for rank_idx in ranked_indices[:k]:
            retrieved_assessments.append(self.assessments[rank_idx])
            
        return retrieved_assessments
