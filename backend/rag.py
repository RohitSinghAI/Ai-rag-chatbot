import os
import json
import re

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ==================================================
# RAG DATA DIRECTORY
# ==================================================

RAG_DIR = "rag_data"

os.makedirs(
    RAG_DIR,
    exist_ok=True
)


# ==================================================
# EMBEDDING MODEL
# ==================================================

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


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

    words = text.split()
    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk = " ".join(
            words[start:end]
        )

        if chunk.strip():
            chunks.append(
                chunk.strip()
            )

        start += (
            chunk_size - overlap
        )

    return chunks


# ==================================================
# CREATE EMBEDDINGS
# ==================================================

def create_embeddings(chunks):

    if not chunks:
        return np.array(
            [],
            dtype="float32"
        )

    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embeddings.astype(
        "float32"
    )


# ==================================================
# CREATE VECTOR INDEX
# ==================================================

def create_vector_index(
    document_id,
    text
):

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
        "document_id": document_id,
        "chunks": len(chunks)
    }


# ==================================================
# CLEAN QUERY
# ==================================================

def clean_query(query):

    if not query:
        return []

    query = query.lower()

    # Keep Unicode letters/numbers so Hindi queries
    # are not removed.
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

    useful_words = [
        word
        for word in words
        if word not in stop_words
    ]

    return useful_words


# ==================================================
# DOCUMENT-WIDE QUERY DETECTION
# ==================================================

def is_document_wide_query(query):

    if not query:
        return False

    query_lower = query.lower().strip()

    patterns = [
        "summarize",
        "summary",
        "main topics",
        "key points",
        "important points",
        "important concepts",
        "main points",
        "overview",
        "give me an overview",
        "explain this pdf",
        "explain the pdf",
        "what is this pdf about",
        "what is this document about",
        "tell me about this pdf",
        "tell me about this document",
        "सारांश",
        "मुख्य विषय",
        "मुख्य बिंदु",
        "जरूरी बिंदु"
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

    query_words = clean_query(
        query
    )

    if not query_words:
        return 0.0

    text_lower = text.lower()

    score = 0.0

    for word in query_words:

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

    if not query or not query.strip():
        return []

    index_path = os.path.join(
        RAG_DIR,
        f"{document_id}.index"
    )

    chunks_path = os.path.join(
        RAG_DIR,
        f"{document_id}.json"
    )

    if not os.path.exists(
        index_path
    ):
        return []

    if not os.path.exists(
        chunks_path
    ):
        return []

    try:

        index = faiss.read_index(
            index_path
        )

        with open(
            chunks_path,
            "r",
            encoding="utf-8"
        ) as file:

            chunks = json.load(
                file
            )

    except Exception as error:

        print(
            "RAG file read error:",
            error
        )

        return []

    if not chunks:
        return []

    # ==================================================
    # VECTOR SEARCH
    # ==================================================

    try:

        query_embedding = embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        query_embedding = (
            query_embedding
            .astype("float32")
        )

        search_count = min(
            max(top_k * 3, 10),
            len(chunks)
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

        if index_id < 0:
            continue

        if index_id >= len(chunks):
            continue

        if index_id in seen:
            continue

        seen.add(index_id)

        text = chunks[index_id]

        k_score = keyword_score(
            query,
            text
        )

        final_score = (
            float(vector_score) * 0.70
            +
            k_score * 0.30
        )

        # A summary/overview query refers to the
        # document as a whole. Therefore the retrieved
        # chunks are considered relevant even when the
        # words "summarize" or "overview" do not appear
        # inside the PDF.
        if document_wide:
            final_score = max(
                final_score,
                0.50
            )

        results.append({
            "text": text,
            "score": float(final_score),
            "vector_score": float(vector_score),
            "keyword_score": float(k_score)
        })

    # ==================================================
    # SORT
    # ==================================================

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ==================================================
    # RETURN TOP RESULTS
    # ==================================================

    return results[
        :top_k
    ]
