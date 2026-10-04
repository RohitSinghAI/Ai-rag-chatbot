import os
import json
import re

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ==================================================
# RAG DATA DIRECTORY
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RAG_DIR = os.path.join(
    BASE_DIR,
    "rag_data"
)

os.makedirs(
    RAG_DIR,
    exist_ok=True
)


# ==================================================
# EMBEDDING MODEL
# ==================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded.")


# ==================================================
# CREATE CHUNKS
# ==================================================

def create_chunks(
    text,
    chunk_size=300,
    overlap=50
):

    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be >= 0 and smaller than chunk_size."
        )

    words = text.split()

    if not words:
        return []

    chunks = []

    step = chunk_size - overlap

    start = 0

    while start < len(words):

        end = min(
            start + chunk_size,
            len(words)
        )

        chunk = " ".join(
            words[start:end]
        ).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start += step

    return chunks


# ==================================================
# CREATE EMBEDDINGS
# ==================================================

def create_embeddings(chunks):

    if not chunks:
        return np.empty(
            (0, 0),
            dtype="float32"
        )

    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32"
    )

    if embeddings.ndim == 1:

        embeddings = embeddings.reshape(
            1,
            -1
        )

    return embeddings


# ==================================================
# CREATE VECTOR INDEX
# ==================================================

def create_vector_index(
    document_id,
    text
):

    if not document_id:
        raise ValueError(
            "document_id is required."
        )

    chunks = create_chunks(
        text
    )

    if not chunks:
        raise ValueError(
            "No text found in document."
        )

    embeddings = create_embeddings(
        chunks
    )

    if embeddings.size == 0:
        raise ValueError(
            "Failed to create embeddings."
        )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    index_path = os.path.join(
        RAG_DIR,
        f"{document_id}.index"
    )

    chunks_path = os.path.join(
        RAG_DIR,
        f"{document_id}.json"
    )

    faiss.write_index(
        index,
        index_path
    )

    with open(
        chunks_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chunks,
            file,
            ensure_ascii=False,
            indent=2
        )

    return {
        "document_id": str(document_id),
        "chunks": len(chunks)
    }


# ==================================================
# CLEAN QUERY
# ==================================================

def clean_query(query):

    if not query or not query.strip():
        return []

    query = query.lower()

    query = re.sub(
        r"[^\w\s]",
        " ",
        query,
        flags=re.UNICODE
    )

    stop_words = {
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "in",
        "on",
        "of",
        "my",
        "me",
        "tell",
        "about",
        "please",
        "can",
        "you",
        "do",
        "i",
        "where",
        "when",
        "how",
        "this",
        "that",
        "these",
        "those",
        "document",
        "pdf",
        "file",
        "from",
        "for",
        "to",
        "and",
        "or",
        "it",
        "be",
        "with"
    }

    words = query.split()

    return [
        word
        for word in words
        if word not in stop_words
    ]


# ==================================================
# DOCUMENT-WIDE QUERY
# ==================================================

def is_document_wide_query(query):

    if not query or not query.strip():
        return False

    query_lower = query.lower().strip()

    patterns = [
        "summarize",
        "summarise",
        "summary",
        "main topics",
        "key points",
        "important points",
        "important concepts",
        "main points",
        "overview",
        "explain this pdf",
        "explain the pdf",
        "explain this document",
        "explain the document",
        "what is this pdf about",
        "what is this document about",
        "tell me about this pdf",
        "tell me about this document",
        "summarize this",
        "summarise this",

        # Hindi
        "सारांश",
        "सारांश बताओ",
        "मुख्य विषय",
        "मुख्य बिंदु",
        "जरूरी बिंदु",
        "महत्वपूर्ण बिंदु",
        "इसका सारांश",
        "इस pdf का सारांश",
        "इस डॉक्यूमेंट का सारांश"
    ]

    return any(
        pattern in query_lower
        for pattern in patterns
    )


# ==================================================
# KEYWORD SCORE
# ==================================================

def keyword_score(
    query,
    text
):

    if not query or not text:
        return 0.0

    query_words = clean_query(
        query
    )

    if not query_words:
        return 0.0

    text_lower = text.lower()

    score = 0.0

    for word in query_words:

        if re.match(
            r"^[A-Za-z0-9_]+$",
            word
        ):

            pattern = (
                r"\b"
                + re.escape(word)
                + r"\b"
            )

            matches = re.findall(
                pattern,
                text_lower,
                flags=re.UNICODE
            )

        else:

            matches = re.findall(
                re.escape(word),
                text_lower,
                flags=re.UNICODE
            )

        if matches:

            score += min(
                len(matches) * 0.20,
                0.60
            )

    original_query = (
        query
        .lower()
        .strip()
    )

    if (
        original_query
        and original_query in text_lower
    ):

        score += 0.50

    return min(
        score,
        1.0
    )


# ==================================================
# SEARCH DOCUMENT
# ==================================================

def search_document(
    document_id,
    query,
    top_k=5
):

    if not document_id:
        return []

    if not query or not query.strip():
        return []

    try:
        top_k = int(top_k)

    except (
        TypeError,
        ValueError
    ):
        top_k = 5

    if top_k <= 0:
        return []

    index_path = os.path.join(
        RAG_DIR,
        f"{document_id}.index"
    )

    chunks_path = os.path.join(
        RAG_DIR,
        f"{document_id}.json"
    )

    if not os.path.exists(index_path):

        print(
            f"RAG index not found: {index_path}"
        )

        return []

    if not os.path.exists(chunks_path):

        print(
            f"RAG chunks not found: {chunks_path}"
        )

        return []

    # ==================================================
    # LOAD INDEX
    # ==================================================

    try:

        index = faiss.read_index(
            index_path
        )

        with open(
            chunks_path,
            "r",
            encoding="utf-8"
        ) as file:

            chunks = json.load(file)

    except Exception as error:

        print(
            "RAG file read error:",
            error
        )

        return []

    if not chunks:
        return []

    if index.ntotal == 0:
        return []

    total_vectors = min(
        index.ntotal,
        len(chunks)
    )

    if total_vectors == 0:
        return []

    # ==================================================
    # QUERY EMBEDDING
    # ==================================================

    try:

        query_embedding = embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype="float32"
        )

        if query_embedding.ndim == 1:

            query_embedding = (
                query_embedding.reshape(
                    1,
                    -1
                )
            )

        if query_embedding.shape[1] != index.d:

            print(
                "Embedding dimension mismatch:",
                query_embedding.shape[1],
                "!=",
                index.d
            )

            return []

        search_count = min(
            max(top_k * 3, 10),
            total_vectors
        )

        vector_scores, indices = index.search(
            query_embedding,
            search_count
        )

    except Exception as error:

        print(
            "RAG search error:",
            error
        )

        return []

    # ==================================================
    # HYBRID RANKING
    # ==================================================

    results = []

    seen = set()

    document_wide = is_document_wide_query(
        query
    )

    for vector_score, index_id in zip(
        vector_scores[0],
        indices[0]
    ):

        index_id = int(index_id)

        if index_id < 0:
            continue

        if index_id >= total_vectors:
            continue

        if index_id in seen:
            continue

        seen.add(index_id)

        text = chunks[index_id]

        if not text or not str(text).strip():
            continue

        text = str(text).strip()

        k_score = keyword_score(
            query,
            text
        )

        vector_score = float(
            vector_score
        )

        final_score = (
            vector_score * 0.70
            +
            k_score * 0.30
        )

        if document_wide:

            final_score = max(
                final_score,
                0.50
            )

        results.append({
            "text": text,
            "score": float(final_score),
            "vector_score": vector_score,
            "keyword_score": float(k_score)
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]