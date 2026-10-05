import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class RAGEngine:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chunks = []
        self.index = None

    def create_chunks(self, pages, chunk_size=1000, overlap=150):

        chunks = []

        for page_number, page_text in pages:

            text = page_text.replace("\x00", " ")
            text = " ".join(text.split())

            if not text.strip():
                continue

            start = 0

            while start < len(text):

                end = start + chunk_size

                chunk = text[start:end]

                if chunk.strip():

                    chunks.append({
                        "text": chunk.strip(),
                        "page": page_number
                    })

                start += chunk_size - overlap

        return chunks

    def build_index(self, pages):

        self.chunks = self.create_chunks(pages)

        if not self.chunks:

            self.index = None

            return 0

        texts = [
            chunk["text"]
            for chunk in self.chunks
        ]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True
        )

        embeddings = embeddings.astype("float32")

        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)

        self.index.add(embeddings)

        return len(self.chunks)

    def search(self, query, top_k=4):

        if self.index is None:

            return []

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True
        )

        query_embedding = query_embedding.astype("float32")

        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(
            query_embedding,
            min(top_k, len(self.chunks))
        )

        results = []

        for score, index in zip(
            scores[0],
            indices[0]
        ):

            if index >= 0:

                results.append({
                    "text": self.chunks[index]["text"],
                    "page": self.chunks[index]["page"],
                    "score": float(score)
                })

        return results