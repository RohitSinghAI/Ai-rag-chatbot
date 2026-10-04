import os
import shutil
import uuid

from fastapi import FastAPI, UploadFimport os
import io
import sqlite3
import uuid
from datetime import datetime

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from pypdf import PdfReader

from dotenv import load_dotenv

from groq import Groq

from rag import (
    create_vector_index,
    search_document
)


# ==================================================
# ENV
# ==================================================

load_dotenv()


# ==================================================
# APP
# ==================================================

app = FastAPI(
    title="AI Study Assistant API"
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "*"
    ],

    allow_credentials=False,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ]
)


# ==================================================
# PATHS
# ==================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "study_assistant.db"
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==================================================
# GROQ
# ==================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

groq_client = None

if GROQ_API_KEY:

    groq_client = Groq(
        api_key=GROQ_API_KEY
    )

else:

    print(
        "WARNING: GROQ_API_KEY not found."
    )


# ==================================================
# DATABASE
# ==================================================

def get_db():

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = (
        sqlite3.Row
    )

    return connection


def init_db():

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,

            FOREIGN KEY(chat_id)
            REFERENCES chats(id)
            ON DELETE CASCADE
        )
    """)

    connection.commit()

    connection.close()


init_db()


# ==================================================
# SCHEMAS
# ==================================================

class ChatRequest(BaseModel):

    chat_id: int

    message: str

    document_id: str | None = None


# ==================================================
# HEALTH
# ==================================================

@app.get("/")
def root():

    return {
        "success": True,
        "message": "AI Study Assistant API is running"
    }


@app.get("/health")
def health():

    return {
        "success": True,
        "groq_configured": bool(
            GROQ_API_KEY
        )
    }


# ==================================================
# CREATE CHAT
# ==================================================

@app.post("/chats")
def create_chat():

    now = datetime.utcnow().isoformat()

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO chats (
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?)
        """,
        (
            "New Chat",
            now,
            now
        )
    )

    chat_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return {
        "success": True,
        "chat_id": chat_id
    }


# ==================================================
# GET ALL CHATS
# ==================================================

@app.get("/chats")
def get_chats():

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM chats
        ORDER BY updated_at DESC
        """
    )

    chats = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return chats


# ==================================================
# GET CHAT MESSAGES
# ==================================================

@app.get("/chats/{chat_id}")
def get_chat(
    chat_id: int
):

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            role,
            content,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,)
    )

    messages = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return messages


# ==================================================
# DELETE CHAT
# ==================================================

@app.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: int
):

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE chat_id = ?
        """,
        (chat_id,)
    )

    cursor.execute(
        """
        DELETE FROM chats
        WHERE id = ?
        """,
        (chat_id,)
    )

    deleted = cursor.rowcount

    connection.commit()

    connection.close()

    if deleted == 0:

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    return {
        "success": True,
        "message": "Chat deleted"
    }


# ==================================================
# PDF TEXT EXTRACTION
# ==================================================

def extract_pdf_text(
    file_bytes: bytes
):

    try:

        reader = PdfReader(
            io.BytesIO(file_bytes)
        )

    except Exception as error:

        raise ValueError(
            f"Invalid PDF file: {error}"
        )

    pages_text = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text()

        except Exception as error:

            print(
                f"Page {page_number} extraction error:",
                error
            )

            text = ""

        if text:

            pages_text.append(
                text.strip()
            )

    full_text = "\n\n".join(
        pages_text
    ).strip()

    return (
        full_text,
        len(reader.pages)
    )


# ==================================================
# PDF UPLOAD
# ==================================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    # ==================================================
    # CHECK FILE NAME
    # ==================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )


    # ==================================================
    # CHECK PDF
    # ==================================================

    filename_lower = (
        file.filename
        .lower()
    )

    if not filename_lower.endswith(
        ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )


    # ==================================================
    # READ FILE
    # ==================================================

    try:

        file_bytes = await file.read()

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read uploaded file: {error}"
        )


    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty."
        )


    # ==================================================
    # SIZE CHECK
    # ==================================================

    max_size = 20 * 1024 * 1024

    if len(file_bytes) > max_size:

        raise HTTPException(
            status_code=413,
            detail="PDF size must be less than 20 MB."
        )


    # ==================================================
    # EXTRACT TEXT
    # ==================================================

    try:

        text, pages = extract_pdf_text(
            file_bytes
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    if not text:

        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text found in this PDF. "
                "If it is a scanned PDF, OCR is required."
            )
        )


    # ==================================================
    # DOCUMENT ID
    # ==================================================

    document_id = str(
        uuid.uuid4()
    )


    # ==================================================
    # SAVE ORIGINAL PDF
    # ==================================================

    safe_filename = (
        os.path.basename(
            file.filename
        )
    )

    pdf_path = os.path.join(
        UPLOAD_DIR,
        f"{document_id}_{safe_filename}"
    )

    try:

        with open(
            pdf_path,
            "wb"
        ) as pdf_file:

            pdf_file.write(
                file_bytes
            )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to save PDF: {error}"
        )


    # ==================================================
    # CREATE RAG INDEX
    # ==================================================

    try:

        rag_result = create_vector_index(
            document_id,
            text
        )

    except Exception as error:

        # Remove uploaded PDF if indexing fails
        try:

            if os.path.exists(
                pdf_path
            ):
                os.remove(
                    pdf_path
                )

        except Exception:
            pass

        print(
            "RAG creation error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=f"RAG processing failed: {error}"
        )


    # ==================================================
    # SUCCESS
    # ==================================================

    return {
        "success": True,
        "document_id": str(document_id),
        "filename": safe_filename,
        "pages": pages,
        "chunks": rag_result["chunks"],
        "message": "PDF uploaded and processed successfully."
    }


# ==================================================
# BUILD CHAT HISTORY
# ==================================================

def get_chat_history(
    chat_id: int,
    limit=12
):

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            chat_id,
            limit
        )
    )

    rows = cursor.fetchall()

    connection.close()

    rows.reverse()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


# ==================================================
# GENERATE AI RESPONSE
# ==================================================

def generate_ai_response(
    message,
    history,
    context=""
):

    if not groq_client:

        return (
            "Groq API key is not configured. "
            "Please add GROQ_API_KEY to your .env file."
        )


    system_prompt = """
You are an AI Study Assistant.

Your job is to help the user understand
study material clearly.

Rules:

1. If document context is provided, answer
   primarily from that context.

2. Do not invent facts that are not supported
   by the document.

3. If the answer is not available in the
   document, clearly say that it is not
   available in the uploaded document.

4. For general questions without document
   context, answer normally.

5. Explain technical topics simply.

6. You can answer in English, Hindi, or
   Hinglish according to the user's language.

7. Use clean formatting with headings and
   bullet points when useful.
"""


    if context:

        system_prompt += f"""

DOCUMENT CONTEXT:

{context}

END DOCUMENT CONTEXT.
"""


    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]


    messages.extend(
        history
    )


    messages.append(
        {
            "role": "user",
            "content": message
        }
    )


    try:

        completion = (
            groq_client
            .chat
            .completions
            .create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=2048
            )
        )

        return (
            completion
            .choices[0]
            .message
            .content
        )

    except Exception as error:

        print(
            "Groq error:",
            error
        )

        raise RuntimeError(
            f"AI response failed: {error}"
        )


# ==================================================
# CHAT
# ==================================================

@app.post("/chat")
def chat(
    request: ChatRequest
):

    message = (
        request.message
        .strip()
    )


    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )


    # ==================================================
    # CHECK CHAT
    # ==================================================

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM chats
        WHERE id = ?
        """,
        (request.chat_id,)
    )

    chat_exists = cursor.fetchone()

    connection.close()


    if not chat_exists:

        raise HTTPException(
            status_code=404,
            detail="Chat not found."
        )


    # ==================================================
    # SAVE USER MESSAGE
    # ==================================================

    now = datetime.utcnow().isoformat()

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            request.chat_id,
            "user",
            message,
            now
        )
    )

    connection.commit()

    connection.close()


    # ==================================================
    # RAG SEARCH
    # ==================================================

    context = ""

    used_rag = False

    rag_results = []


    if request.document_id:

        rag_results = search_document(
            request.document_id,
            message,
            top_k=8
        )


        if rag_results:

            used_rag = True

            context_parts = []

            for result in rag_results:

                context_parts.append(
                    result["text"]
                )

            context = "\n\n---\n\n".join(
                context_parts
            )


    # ==================================================
    # CHAT HISTORY
    # ==================================================

    history = get_chat_history(
        request.chat_id,
        limit=12
    )


    # Remove latest user message because
    # it will be sent separately.
    if history:

        last = history[-1]

        if (
            last["role"] == "user"
            and last["content"] == message
        ):

            history = history[:-1]


    # ==================================================
    # AI RESPONSE
    # ==================================================

    try:

        response_text = generate_ai_response(
            message,
            history,
            context
        )

    except Exception as error:

        # Remove user message if AI fails
        connection = get_db()

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM messages
            WHERE id = (
                SELECT MAX(id)
                FROM messages
                WHERE chat_id = ?
            )
            """,
            (request.chat_id,)
        )

        connection.commit()

        connection.close()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    # ==================================================
    # SAVE AI RESPONSE
    # ==================================================

    now = datetime.utcnow().isoformat()

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            request.chat_id,
            "assistant",
            response_text,
            now
        )
    )


    # ==================================================
    # UPDATE CHAT TITLE
    # ==================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE chat_id = ?
        """,
        (request.chat_id,)
    )

    message_count = cursor.fetchone()[0]


    if message_count <= 2:

        title = message[:50]

        cursor.execute(
            """
            UPDATE chats
            SET
                title = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                now,
                request.chat_id
            )
        )

    else:

        cursor.execute(
            """
            UPDATE chats
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                request.chat_id
            )
        )


    connection.commit()

    connection.close()


    return {
        "success": True,
        "chat_id": request.chat_id,
        "response": response_text,
        "used_rag": used_rag,
        "document_id": request.document_id,
        "sources": len(rag_results)
    }


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )ile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import pymupdf

from database import get_connection, create_tables

from rag import (
    create_vector_index,
    search_document,
)


# ==================================================
# Environment
# ==================================================

load_dotenv()


# ==================================================
# FastAPI
# ==================================================

app = FastAPI(
    title="AI Chatbot API",
    version="1.0.0",
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# Groq Client
# ==================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set.")

client = Groq(api_key=GROQ_API_KEY)


# ==================================================
# Database
# ==================================================

create_tables()


# ==================================================
# Upload Directory
# ==================================================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True,
)


# ==================================================
# Request Model
# ==================================================

class ChatRequest(BaseModel):
    chat_id: int | None = None
    message: str
    document_id: str | None = None


# ==================================================
# HOME
# ==================================================

@app.get("/")
def home():
    return {
        "message": "AI Chatbot Backend is running!"
    }


# ==================================================
# CHAT APIs
# ==================================================


# --------------------------------------------------
# Create New Chat
# --------------------------------------------------

@app.post("/chats")
def create_chat():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO chats (title)
            VALUES (?)
            """,
            ("New Chat",),
        )

        chat_id = cursor.lastrowid

        connection.commit()

        return {
            "chat_id": chat_id,
            "title": "New Chat",
        }

    except Exception as error:
        connection.rollback()
        print("Create Chat Error:", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to create chat",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Get All Chats
# --------------------------------------------------

@app.get("/chats")
def get_chats():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, title, created_at
            FROM chats
            ORDER BY id DESC
            """
        )

        chats = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return chats

    except Exception as error:
        print("Get Chats Error:", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch chats",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Get Chat Messages
# --------------------------------------------------

@app.get("/chats/{chat_id}")
def get_chat_messages(chat_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        )

        messages = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return messages

    except Exception as error:
        print("Get Chat Messages Error:", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch chat messages",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Delete Chat
# --------------------------------------------------

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Delete messages
        cursor.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            """,
            (chat_id,),
        )

        # Delete chat
        cursor.execute(
            """
            DELETE FROM chats
            WHERE id = ?
            """,
            (chat_id,),
        )

        if cursor.rowcount == 0:
            connection.rollback()

            return {
                "success": False,
                "message": "Chat not found",
            }

        connection.commit()

        return {
            "success": True,
            "message": "Chat deleted successfully",
            "chat_id": chat_id,
        }

    except Exception as error:
        connection.rollback()

        print("Delete Chat Error:", error)

        return {
            "success": False,
            "message": "Failed to delete chat",
        }

    finally:
        connection.close()


# ==================================================
# CHAT WITH AI + RAG
# ==================================================

@app.post("/chat")
def chat(request: ChatRequest):

    # Validate message
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ==================================================
        # CREATE CHAT
        # ==================================================

        chat_id = request.chat_id

        if chat_id is None:

            cursor.execute(
                """
                INSERT INTO chats (title)
                VALUES (?)
                """,
                ("New Chat",),
            )

            chat_id = cursor.lastrowid

        else:

            # Check whether chat exists
            cursor.execute(
                """
                SELECT id
                FROM chats
                WHERE id = ?
                """,
                (chat_id,),
            )

            chat_exists = cursor.fetchone()

            if not chat_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Chat not found.",
                )

        # ==================================================
        # GET PREVIOUS CHAT HISTORY
        # IMPORTANT:
        # Fetch history BEFORE inserting current message.
        # This prevents duplicate current user message.
        # ==================================================

        cursor.execute(
            """
            SELECT role, content
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        )

        previous_messages = cursor.fetchall()

        # ==================================================
        # SYSTEM PROMPT
        # ==================================================

        system_prompt = """
You are a helpful AI assistant.

Rules:

1. Give short and clear answers.
2. Answer exactly what the user asks.
3. For simple questions, answer in 1-3 sentences.
4. Do not repeat the user's question.
5. Be professional and friendly.
6. You can have normal conversations.
7. Answer general questions using your general knowledge.
8. If relevant document information is provided, use it.
9. Never force a document answer for a general conversation.
10. Never say information is missing from the document unless
    the user specifically asks about the document and the
    information is genuinely unavailable.
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        # ==================================================
        # ADD CONVERSATION HISTORY
        # ==================================================

        for previous_message in previous_messages:

            role = previous_message["role"]

            # Only allow valid Groq roles
            if role not in ("user", "assistant"):
                continue

            messages.append(
                {
                    "role": role,
                    "content": previous_message["content"],
                }
            )

        # ==================================================
        # RAG SEARCH
        # ==================================================

        document_context = ""
        use_rag = False

        if request.document_id:

            try:

                results = search_document(
                    request.document_id,
                    user_message,
                    top_k=8,
                )

                # ------------------------------------------
                # Detect document-specific questions
                # ------------------------------------------

                document_words = [
                    "pdf",
                    "document",
                    "file",
                    "this",
                    "summarize",
                    "summary",
                    "main topics",
                    "key points",
                    "important concepts",
                    "explain",
                    "list the key",
                    "according to",
                ]

                message_lower = user_message.lower()

                is_document_question = any(
                    word in message_lower
                    for word in document_words
                )

                # ------------------------------------------
                # Select relevant chunks
                # ------------------------------------------

                if is_document_question:

                    # For explicit document questions,
                    # use the best retrieved chunks.
                    relevant_results = results[:8]

                else:

                    relevant_results = [
                        result
                        for result in results
                        if (
                            result.get("score", 0) >= 0.45
                            or
                            result.get("keyword_score", 0) >= 0.20
                        )
                    ]

                # ------------------------------------------
                # Create document context
                # ------------------------------------------

                if relevant_results:

                    use_rag = True

                    document_context = "\n\n".join(
                        result.get("text", "")
                        for result in relevant_results
                        if result.get("text")
                    )

            except Exception as error:

                print(
                    "RAG Search Error:",
                    error,
                )

                use_rag = False
                document_context = ""

        # ==================================================
        # ADD RAG CONTEXT
        # ==================================================

        if use_rag:

            messages.append(
                {
                    "role": "system",
                    "content": f"""
The user has uploaded a document.

The following information was retrieved
from that document:

-------------------------
{document_context}
-------------------------

Use this information when the user's
question is related to the uploaded document.

If the question is general or unrelated
to the document, answer normally.

Do not invent information from the document.
""",
                }
            )

        # ==================================================
        # ADD CURRENT USER MESSAGE
        # IMPORTANT:
        # This is added ONLY ONCE.
        # ==================================================

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        # ==================================================
        # GROQ
        # ==================================================

        try:

            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.3,
                max_tokens=700,
            )

            ai_response = (
                response
                .choices[0]
                .message
                .content
                .strip()
            )

            if not ai_response:
                ai_response = (
                    "Sorry, I couldn't generate a response."
                )

        except Exception as error:

            print(
                "Groq Error:",
                error,
            )

            connection.rollback()

            return {
                "chat_id": chat_id,
                "response": "Sorry, something went wrong while generating the response.",
                "used_rag": use_rag,
            }

        # ==================================================
        # SAVE USER MESSAGE
        # ==================================================

        cursor.execute(
            """
            INSERT INTO messages
            (chat_id, role, content)
            VALUES (?, ?, ?)
            """,
            (
                chat_id,
                "user",
                user_message,
            ),
        )

        # ==================================================
        # SAVE AI RESPONSE
        # ==================================================

        cursor.execute(
            """
            INSERT INTO messages
            (chat_id, role, content)
            VALUES (?, ?, ?)
            """,
            (
                chat_id,
                "assistant",
                ai_response,
            ),
        )

        # ==================================================
        # UPDATE CHAT TITLE
        # ==================================================

        title = user_message[:40].strip()

        if len(user_message) > 40:
            title += "..."

        cursor.execute(
            """
            UPDATE chats
            SET title = ?
            WHERE id = ?
            AND title = 'New Chat'
            """,
            (
                title,
                chat_id,
            ),
        )

        # ==================================================
        # COMMIT
        # ==================================================

        connection.commit()

        # ==================================================
        # RETURN
        # ==================================================

        return {
            "chat_id": chat_id,
            "response": ai_response,
            "used_rag": use_rag,
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:

        connection.rollback()

        print(
            "Chat Error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process chat.",
        )

    finally:
        connection.close()


# ==================================================
# PDF UPLOAD + RAG
# ==================================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
):

    # ==================================================
    # Check PDF
    # ==================================================

    if file.content_type != "application/pdf":

        return {
            "success": False,
            "message": "Only PDF files are allowed.",
        }

    # ==================================================
    # Check filename
    # ==================================================

    if not file.filename:

        return {
            "success": False,
            "message": "Invalid file name.",
        }

    # ==================================================
    # Generate Document ID
    # ==================================================

    document_id = str(
        uuid.uuid4()
    )

    # ==================================================
    # Secure File Name
    # ==================================================

    filename = os.path.basename(
        file.filename
    )

    # ==================================================
    # File Path
    # ==================================================

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{document_id}_{filename}",
    )

    # ==================================================
    # Save PDF
    # ==================================================

    try:

        with open(
            file_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as error:

        print(
            "File Save Error:",
            error,
        )

        return {
            "success": False,
            "message": "Failed to save PDF.",
        }

    # ==================================================
    # Read PDF + Extract Text
    # ==================================================

    text = ""
    total_pages = 0

    try:

        pdf_document = pymupdf.open(
            file_path
        )

        total_pages = len(
            pdf_document
        )

        for page_number, page in enumerate(
            pdf_document
        ):

            try:

                page_text = page.get_text(
                    "text"
                )

                if page_text:

                    text += page_text
                    text += "\n"

            except Exception as page_error:

                print(
                    f"PDF Page {page_number + 1} Error:",
                    page_error,
                )

        pdf_document.close()

    except Exception as error:

        print(
            "PDF Read Error:",
            error,
        )

        # Cleanup file
        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception:
            pass

        return {
            "success": False,
            "message": "Failed to read PDF.",
        }

    # ==================================================
    # Clean Extracted Text
    # ==================================================

    text = text.strip()

    # ==================================================
    # Check Extracted Text
    # ==================================================

    if not text:

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as cleanup_error:

            print(
                "PDF Cleanup Error:",
                cleanup_error,
            )

        return {
            "success": False,
            "message": (
                "Could not extract text from this PDF. "
                "The PDF may be scanned/image-based or "
                "contain no selectable text."
            ),
        }

    # ==================================================
    # Create RAG Vector Index
    # ==================================================

    try:

        rag_result = create_vector_index(
            document_id,
            text,
        )

    except Exception as error:

        print(
            "RAG Index Error:",
            error,
        )

        # Cleanup PDF if RAG processing fails
        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception:
            pass

        return {
            "success": False,
            "message": "Failed to create RAG index.",
        }

    # ==================================================
    # Return
    # ==================================================

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "pages": total_pages,
        "text_length": len(text),
        "chunks": rag_result.get("chunks", 0),
        "message": "PDF processed successfully.",
    }
