import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import faiss
import numpy as np
import pickle

from config import VECTOR_DB_DIR


class FAISSVectorStore:

    def __init__(self):
        self.index = None
        self.documents = []

    def build_index(self, embeddings, documents):
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype(np.float32))
        self.documents = list(documents)

    def add_documents(self, embeddings, documents):
        """Incrementally adds new vector embeddings and documents to the existing index without re-indexing."""
        if self.index is None:
            self.build_index(embeddings, documents)
            return
        self.index.add(embeddings.astype(np.float32))
        self.documents.extend(documents)

    def save(self, target_dir=None):
        out_dir = Path(target_dir) if target_dir else VECTOR_DB_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(
            self.index,
            str(out_dir / "index.faiss")
        )

        with open(out_dir / "documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)

    def load(self, source_dir=None):
        in_dir = Path(source_dir) if source_dir else VECTOR_DB_DIR
        self.index = faiss.read_index(
            str(in_dir / "index.faiss")
        )

        with open(in_dir / "documents.pkl", "rb") as f:
            self.documents = pickle.load(f)

    def search(self, query_embedding, top_k=4):
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1).astype(np.float32),
            top_k
        )

        results = []

        for distance, idx in zip(distances[0], indices[0]):

            if idx == -1:
                # FAISS pads with -1 when fewer than top_k matches exist
                continue

            doc = self.documents[idx]

            # Attach the raw L2 distance to metadata so downstream
            # consumers (evaluator, prompt builder, etc.) can access it
            # without changing the return shape of search().
            # Handles both LangChain-style Document objects and
            # plain-dict documents (e.g. {"page_content": ..., "metadata": {...}}).
            if isinstance(doc, dict):
                doc.setdefault("metadata", {})
                doc["metadata"]["score"] = float(distance)
            else:
                doc.metadata["score"] = float(distance)

            results.append(doc)

        return results