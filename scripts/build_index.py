import os
import sys
import json
import pickle
import numpy as np
import faiss
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.models.domain import Assessment

TYPE_MAP = {
    "A": "Ability and Aptitude cognitive test",
    "B": "Biodata and Situational Judgement behavioral test",
    "C": "Competencies evaluation",
    "D": "Development and 360 degree feedback",
    "E": "Assessment Exercises practical test",
    "K": "Knowledge and Skills technical test",
    "P": "Personality and Behavior psychometric test",
    "S": "Simulations hands-on coding test"
}

def build_search_text(item: Dict[str, Any]) -> str:
    """Compile a rich structured text representation for embedding semantic alignment."""
    parts = []
    
    name = item.get("name", "").strip()
    if name:
        parts.append(f"Assessment Name: {name}")
        
    description = item.get("description", "").strip()
    if description:
        parts.append(f"Description: {description}")
        
    category = item.get("category", "").strip()
    if category:
        parts.append(f"Category: {category}")
        
    skills = item.get("skills", [])
    if skills:
        parts.append(f"Measured Skills: {', '.join(skills)}")
        
    job_roles = item.get("job_roles", [])
    if job_roles:
        parts.append(f"Target Job Roles: {', '.join(job_roles)}")
        
    test_types = item.get("test_type", [])
    if test_types:
        mapped_types = [TYPE_MAP.get(t.upper(), t) for t in test_types]
        parts.append(f"Assessment Focus and Format: {', '.join(mapped_types)}")
        
    duration = item.get("duration")
    if duration:
        parts.append(f"Duration: {duration} minutes")
        
    # Append structured keywords to boost relevance of common roles
    name_lower = name.lower()
    keywords = []
    if any(w in name_lower for w in ["java", "python", "sql", "c#", "c++", ".net", "angular", "react", "javascript", "coding", "software"]):
        keywords.extend(["programming", "coding", "software engineering", "developer", "technical skills"])
    if any(w in name_lower for w in ["sales", "marketing", "commercial"]):
        keywords.extend(["selling", "business development", "revenue", "sales representative"])
    if any(w in name_lower for w in ["manager", "leader", "executive", "supervisor"]):
        keywords.extend(["leadership", "people management", "strategic direction", "360 feedback"])
    if any(w in name_lower for w in ["verbal", "numerical", "reasoning", "deductive", "inductive"]):
        keywords.extend(["cognitive ability", "aptitude", "mental reasoning", "problem solving"])
        
    if keywords:
        parts.append(f"Keywords: {', '.join(keywords)}")
        
    return "\n".join(parts)

def main():
    """Load catalog, generate embeddings, and build the FAISS index."""
    print("Initiating FAISS Dense Index Construction...")
    
    # Load processed catalog
    catalog_path = settings.processed_catalog_path
    if not os.path.exists(catalog_path):
        print(f"[ERROR] Catalog file not found at: {catalog_path}. Please run scrape.py first.")
        sys.exit(1)
        
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    if not catalog:
        print("[ERROR] Catalog is empty. Aborting indexing.")
        sys.exit(1)
        
    print(f"Loaded {len(catalog)} assessments from catalog.")
    
    # Compile text representations & domain models
    corpus = []
    assessments: List[Assessment] = []
    
    for item in catalog:
        text_repr = build_search_text(item)
        corpus.append(text_repr)
        
        # Instantiate domain model
        assessment = Assessment(**item)
        assessments.append(assessment)
        
    # Load SentenceTransformers model
    print(f"Loading embedding model: {settings.embedding_model} ...")
    model = SentenceTransformer(settings.embedding_model)
    
    # Generate embeddings
    print("Generating dense vector representations...")
    embeddings = model.encode(corpus, show_progress_bar=True, convert_to_numpy=True)
    
    # Normalize vectors to support cosine similarity via inner product
    print("Normalizing embeddings...")
    faiss.normalize_L2(embeddings)
    
    # Build FAISS index
    dimension = embeddings.shape[1]
    print(f"Initializing FAISS index (dimension={dimension})...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    # Ensure index directory exists
    os.makedirs(settings.index_dir, exist_ok=True)
    
    # Save index and metadata
    faiss.write_index(index, settings.faiss_index_path)
    print(f"FAISS dense index saved to: {settings.faiss_index_path}")
    
    with open(settings.metadata_path, "wb") as f:
        pickle.dump(assessments, f)
    print(f"Metadata serialized to: {settings.metadata_path}")
    print("Embedding generation completed successfully.")

if __name__ == "__main__":
    main()
